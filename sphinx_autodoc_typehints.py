import inspect
import logging
import re
from sphinx.util.inspect import getargspec
from sphinx.ext.autodoc import formatargspec

try:
    from backports.typing import Optional, get_type_hints
except ImportError:
    from typing import Optional, get_type_hints


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def format_annotation(annotation):
    if inspect.isclass(annotation):
        if annotation.__module__ == 'builtins':
            if annotation.__qualname__ == 'NoneType':
                return '``None``'
            else:
                return ':class:`{}`'.format(annotation.__qualname__)

        extra = ''
        if annotation.__module__ in ('typing', 'backports.typing'):
            if annotation.__qualname__ == 'Union':
                params = annotation.__union_params__
                if params[-1].__qualname__ == 'NoneType':
                    if len(params) > 2:
                        annotation.__union_params__ = params[:-1]
                        params = (annotation,)
                        annotation = Optional
                    else:
                        annotation = Optional
                        params = (params[:-1],)
            else:
                params = getattr(annotation, '__parameters__', None)

            if params:
                extra = '\\[' + ', '.join(format_annotation(param) for param in params) + ']'

        return ':class:`~{}.{}`{}'.format(annotation.__module__, annotation.__qualname__, extra)

    return str(annotation)


def process_signature(app, what: str, name: str, obj, options, signature, return_annotation):
    if callable(obj):
        if what in ('class', 'exception'):
            obj = getattr(obj, '__init__')

        try:
            argspec = getargspec(obj)
        except TypeError:
            return

        if what in ('method', 'class', 'exception') and argspec.args:
            del argspec.args[0]

        return formatargspec(obj, *argspec[:-1]), None


def _process_google_docstrings(type_hints, lines):
    """Process numpy docstrings parameters."""
    for argname, annotation in type_hints.items():
        formatted_annotation = format_annotation(annotation)

        if argname == 'return':
            pass
        else:
            logger.debug('Searching for %s', argname)
            in_args_section = False
            for i, line in enumerate(lines):
                if line == 'Args:':
                    in_args_section = True
                elif in_args_section:
                    if not line.startswith('  '):
                        in_args_section = False
                        break
                    match = re.match('(  +{}) ?:(.*)'.format(argname), line)
                    if match:
                        lines[i] = match.expand('\\1 ({}): \\2'.format(str(formatted_annotation)))
                        logger.debug('line replaced: %s', lines[i])
                        break

def _check_numpy_section_start(lines, i, section=None):
    """Check if numpy section starts at line `i`"""
    return (
        i > 0 and
        i < len(lines) - 1 and
        lines[i + 1].startswith('---') and
        (section and lines[i] == section or
         re.match('\w+:', lines[i]))
    )


def _process_numpy_docstrings(type_hints, lines):
    """Process numpy docstrings parameters."""
    for argname, annotation in type_hints.items():
        formatted_annotation = format_annotation(annotation)

        if argname == 'return':
            pass
        else:
            logger.debug('Searching for %s', argname)
            in_args_section = False
            in_return_section = False
            for i, line in enumerate(lines):
                if _check_numpy_section_start(lines, i - 1, 'Parameters'):
                    logger.debug('Numpy parameters section ended on line %i', i)
                    in_args_section = True
                elif in_args_section:
                    if _check_numpy_section_start(lines, i):
                        in_args_section = False
                        logger.debug('Numpy parameters section ended on line %i', i)
                        break
                    match = re.match('{}( ?: ?)?'.format(argname), line)
                    if match:
                        lines[i] = argname + ' : ' + formatted_annotation
                        logger.debug('line replaced: %s', lines[i])
                        break
                elif (_check_numpy_section_start(lines, i, 'Returns') or
                      _check_numpy_section_start(lines, i, 'Yields')):
                    in_return_section = True
                elif in_return_section:
                    if _check_numpy_section_start(lines, i):
                        in_return_section = False
                        logger.debug('Numpy return section ended on line %i', i)
                        break
                    if lines[i - 1].startswith('---') and not line or line == ':':
                        lines[i] = formatted_annotation
                    if i < len(lines) - 1 and lines[i + 1].startswith('---') and re.match('\w+:', line):
                        in_return_section = False
                        logger.debug('Numpy parameters section ended on line %i', i)
                        break


def _process_sphinx_docstrings(type_hints, lines):
    for argname, annotation in type_hints.items():
        formatted_annotation = format_annotation(annotation)

        if argname == 'return':
            insert_index = len(lines)
            for i, line in enumerate(lines):
                if line.startswith(':rtype:'):
                    insert_index = None
                    break
                elif line.startswith(':return:') or line.startswith(':returns:') or line.startswith(''):
                    insert_index = i
                    break

            if insert_index is not None:
                lines.insert(insert_index, ':rtype: {}'.format(formatted_annotation))
        else:
            searchfor = ':param {}:'.format(argname)
            for i, line in enumerate(lines):
                if line.startswith(searchfor):
                    lines.insert(i, ':type {}: {}'.format(argname, formatted_annotation))
                    break


def process_docstring(app, what, name, obj, options, lines):
    if callable(obj):
        if what in ('class', 'exception'):
            obj = getattr(obj, '__init__')

        # Unwrap until we get to the original definition
        while hasattr(obj, '__wrapped__'):
            obj = obj.__wrapped__

        try:
            type_hints = get_type_hints(obj)
        except AttributeError:
            return

        _process_sphinx_docstrings(type_hints, lines)
        _process_google_docstrings(type_hints, lines)
        _process_numpy_docstrings(type_hints, lines)



def setup(app):
    app.connect('autodoc-process-signature', process_signature)
    app.connect('autodoc-process-docstring', process_docstring)
