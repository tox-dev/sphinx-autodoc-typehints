# coding=utf-8
""" Extend typing"""

import inspect
from inspect import unwrap
from io import BytesIO
import re
from tokenize import COMMENT, INDENT, OP, tokenize
from typing import Any, AnyStr, GenericMeta, TypeVar, get_type_hints

from sphinx.ext.autodoc import formatargspec
from sphinx.util import logging
from sphinx.util.inspect import getargspec

TYPE_MARKER = '# type: '

LOGGER = logging.getLogger(__name__)


def format_annotation(annotation):  # pylint: disable=too-many-return-statements
    if inspect.isclass(annotation) and annotation.__module__ == 'builtins':
        if annotation.__qualname__ == 'NoneType':
            return '``None``'
        return ':class:`{}`'.format(annotation.__qualname__)

    annotation_cls = annotation if inspect.isclass(annotation) else type(annotation)
    if annotation_cls.__module__ in ('typing',):
        return format_typing_annotation(annotation, annotation_cls)
    elif annotation is Ellipsis:
        return '...'
    elif inspect.isclass(annotation):
        extra = ''
        if isinstance(annotation, GenericMeta):
            extra = '\\[{}]'.format(', '.join(format_annotation(param)
                                              for param in annotation.__parameters__))

        return ':class:`~{}.{}`{}'.format(annotation.__module__, annotation.__qualname__, extra)
    else:
        return str(annotation)


def format_typing_annotation(annotation, annotation_cls):
    params = None
    prefix = ':class:'
    extra = ''
    class_name = annotation_cls.__qualname__
    if annotation is Any:
        return ':data:`~typing.Any`'
    elif annotation is AnyStr:
        return ':data:`~typing.AnyStr`'
    elif isinstance(annotation, TypeVar):
        return '\\%r' % annotation
    elif class_name in ('Union', '_Union'):
        class_name, params, prefix = format_union_annotation(annotation, class_name, params, prefix)
    elif annotation_cls.__qualname__ == 'Tuple' and hasattr(annotation, '__tuple_params__'):
        # initial behavior, reworked in 3.6
        params = annotation.__tuple_params__  # pragma: no coverage
        if annotation.__tuple_use_ellipsis__:  # pragma: no coverage
            params += (Ellipsis,)  # pragma: no coverage
    elif annotation_cls.__qualname__ == 'Callable':
        params, prefix = format_callable_annotation(annotation, params, prefix)
    elif hasattr(annotation, 'type_var'):
        # Type alias
        class_name = annotation.name
        params = (annotation.type_var,)
    elif getattr(annotation, '__args__', None) is not None:
        params = annotation.__args__
    elif hasattr(annotation, '__parameters__'):
        params = annotation.__parameters__
    if params:
        extra = '\\[{}]'.format(', '.join(format_annotation(param) for param in params))
    return '{}`~typing.{}`{}'.format(prefix, class_name, extra)


def format_callable_annotation(annotation, params, prefix):
    prefix = ':data:'
    arg_annotations = result_annotation = None
    if hasattr(annotation, '__result__'):
        # initial behavior, reworked in 3.6
        arg_annotations = annotation.__args__  # pragma: no coverage
        result_annotation = annotation.__result__  # pragma: no coverage
    elif getattr(annotation, '__args__', None) is not None:
        arg_annotations = annotation.__args__[:-1]
        result_annotation = annotation.__args__[-1]
    if arg_annotations in (Ellipsis, (Ellipsis,)):
        params = [Ellipsis, result_annotation]
    elif arg_annotations is not None:
        params = ['\\[{}]'.format(', '.join(format_annotation(param) for param in arg_annotations)),
                  result_annotation]
    return params, prefix


def format_union_annotation(annotation, class_name, params, prefix):
    prefix = ':data:'
    class_name = 'Union'
    if hasattr(annotation, '__union_params__'):
        # initial behavior, reworked in 3.6
        params = annotation.__union_params__  # pragma: no coverage
    else:
        params = annotation.__args__
    if params and len(params) == 2 and params[1].__qualname__ == 'NoneType':
        class_name = 'Optional'
        params = (params[0],)
    return class_name, params, prefix


# noinspection PyUnusedLocal
def process_signature(app, what: str, name: str, obj,  # pylint: disable=too-many-arguments,unused-argument
                      options, signature, return_annotation):  # pylint: disable=unused-argument
    if callable(obj):
        if what in ('class', 'exception'):
            obj = getattr(obj, '__init__')

        obj = unwrap(obj)
        try:
            argspec = getargspec(obj)
        except TypeError:
            return

        if what in ('method', 'class', 'exception') and argspec.args:
            del argspec.args[0]

        return formatargspec(obj, *argspec[:-1]), None


# noinspection PyUnusedLocal
def process_docstring(app, what, name, obj, options, lines):  # pylint: disable=too-many-arguments,unused-argument
    if isinstance(obj, property):
        obj = obj.fget  # pragma: no coverage

    if callable(obj):
        if what in ('class', 'exception'):
            obj = getattr(obj, '__init__')

        obj = unwrap(obj)
        try:
            type_hints = get_type_hints(obj)
        except (AttributeError, TypeError):
            return  # Introspecting a slot wrapper will raise TypeError

        if not type_hints:
            type_hints = get_comment_type_hint(obj)

        LOGGER.debug('[autodoc-typehints][process-docstring] for %d id %s got %s', id(obj), obj.__qualname__,
                     '|'.join('{} - {}'.format(k, v) for k, v in type_hints.items()))

        insert_type_hints(lines, type_hints, what)


def insert_type_hints(lines, type_hints, what):
    for arg_name, annotation in type_hints.items():
        formatted_annotation = format_annotation(annotation)
        if arg_name == 'return':
            if what in ('class', 'exception'):
                # Don't add return type None from __init__()
                continue

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
            search_for = ':param {}:'.format(arg_name)
            for i, line in enumerate(lines):
                if line.startswith(search_for):
                    lines.insert(i, ':type {}: {}'.format(arg_name, formatted_annotation))
                    break


TYPE_INFO = r'.*:# type: (.*)'
TYPE_COMMENT_RE = re.compile(TYPE_INFO)


def get_comment_type_hint(obj):
    type_hints = {}
    type_info = get_comment_type_str(obj)
    if type_info:
        obj_arg = inspect.signature(obj)
        at_pos = type_info.rfind('->')
        obj_globals = getattr(obj, '__globals__', None)
        types = eval('{}'.format(type_info[:at_pos]), obj_globals)  # pylint: disable=eval-used
        if not isinstance(types, tuple):
            types = [types]
        return_type = eval(type_info[at_pos + 2:], obj_globals)  # pylint: disable=eval-used
        type_hints = {'return': return_type}
        keys = list(obj_arg.parameters.keys())
        if keys and keys[0] == 'self':
            keys = keys[1:]  # skip self
        type_hints.update(dict(zip(keys, types)))
    return type_hints


def get_comment_type_str(obj):
    type_info = ''
    try:
        source = '\n'.join(inspect.getsourcelines(obj)[0]).encode()
        tokens_generator = tokenize(BytesIO(source).readline)
        found_func_end, prev_op = False, None
        for tok_num, tok_val, _, _, _ in tokens_generator:
            if found_func_end is False:
                if tok_num == OP:
                    if prev_op == ')' and tok_val == ':':
                        found_func_end = True
                    prev_op = tok_val
            else:
                if tok_num == INDENT:
                    break
                elif tok_num == COMMENT and tok_val.startswith(TYPE_MARKER):
                    type_info = tok_val[len(TYPE_MARKER):]
                    break
    except (IOError, TypeError):
        pass
    return type_info


def setup(app):
    app.connect('autodoc-process-signature', process_signature)
    app.connect('autodoc-process-docstring', process_docstring)
    return dict(parallel_read_safe=True)
