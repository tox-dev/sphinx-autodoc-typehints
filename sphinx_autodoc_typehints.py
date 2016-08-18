import inspect

from sphinx.util.inspect import getargspec
from sphinx.ext.autodoc import formatargspec

try:
    from backports.typing import Optional, get_type_hints
except ImportError:
    from typing import Optional, get_type_hints


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
                if len(params) == 2 and params[1].__qualname__ == 'NoneType':
                    annotation = Optional
                    params = (params[0],)
            elif annotation.__qualname__ == 'Tuple':
                params = annotation.__tuple_params__
                if annotation.__tuple_use_ellipsis__:
                    params += ('...',)
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

        for argname, annotation in type_hints.items():
            formatted_annotation = format_annotation(annotation)

            if argname == 'return':
                insert_index = len(lines)
                for i, line in enumerate(lines):
                    if line.startswith(':rtype:'):
                        insert_index = None
                        break
                    elif line.startswith(':return:') or line.startswith(':returns:'):
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


def setup(app):
    app.connect('autodoc-process-signature', process_signature)
    app.connect('autodoc-process-docstring', process_docstring)
