import inspect
import textwrap
import typing
from typing import get_type_hints, TypeVar, Any, AnyStr, Generic, Union

from sphinx.util import logging
from sphinx.util.inspect import Signature

try:
    from typing_extensions import Protocol
except ImportError:
    Protocol = None

logger = logging.getLogger(__name__)


def format_annotation(annotation, fully_qualified=False):
    if inspect.isclass(annotation) and annotation.__module__ == 'builtins':
        if annotation.__qualname__ == 'NoneType':
            return '``None``'
        else:
            return ':py:class:`{}`'.format(annotation.__qualname__)

    annotation_cls = annotation if inspect.isclass(annotation) else type(annotation)
    class_name = None
    if annotation_cls.__module__ == 'typing':
        params = None
        prefix = ':py:class:'
        module = 'typing'
        extra = ''

        if inspect.isclass(getattr(annotation, '__origin__', None)):
            annotation_cls = annotation.__origin__
            try:
                mro = annotation_cls.mro()
                if Generic in mro or (Protocol and Protocol in mro):
                    module = annotation_cls.__module__
            except TypeError:
                pass  # annotation_cls was either the "type" object or typing.Type

        if annotation is Any:
            return ':py:data:`{}typing.Any`'.format("" if fully_qualified else "~")
        elif annotation is AnyStr:
            return ':py:data:`{}typing.AnyStr`'.format("" if fully_qualified else "~")
        elif isinstance(annotation, TypeVar):
            return '\\%r' % annotation
        elif (annotation is Union or getattr(annotation, '__origin__', None) is Union or
              hasattr(annotation, '__union_params__')):
            prefix = ':py:data:'
            class_name = 'Union'
            if hasattr(annotation, '__union_params__'):
                params = annotation.__union_params__
            elif hasattr(annotation, '__args__'):
                params = annotation.__args__

            if params and len(params) == 2 and (hasattr(params[1], '__qualname__') and
                                                params[1].__qualname__ == 'NoneType'):
                class_name = 'Optional'
                params = (params[0],)
        elif annotation_cls.__qualname__ == 'Tuple' and hasattr(annotation, '__tuple_params__'):
            params = annotation.__tuple_params__
            if annotation.__tuple_use_ellipsis__:
                params += (Ellipsis,)
        elif annotation_cls.__qualname__ == 'Callable':
            prefix = ':py:data:'
            arg_annotations = result_annotation = None
            if hasattr(annotation, '__result__'):
                arg_annotations = annotation.__args__
                result_annotation = annotation.__result__
            elif getattr(annotation, '__args__', None):
                arg_annotations = annotation.__args__[:-1]
                result_annotation = annotation.__args__[-1]

            if arg_annotations in (Ellipsis, (Ellipsis,)):
                params = [Ellipsis, result_annotation]
            elif arg_annotations is not None:
                params = [
                    '\\[{}]'.format(
                        ', '.join(
                            format_annotation(param, fully_qualified)
                            for param in arg_annotations)),
                    result_annotation
                ]
        elif hasattr(annotation, 'type_var'):
            # Type alias
            class_name = annotation.name
            params = (annotation.type_var,)
        elif getattr(annotation, '__args__', None) is not None:
            params = annotation.__args__
        elif hasattr(annotation, '__parameters__'):
            params = annotation.__parameters__

        if params:
            extra = '\\[{}]'.format(', '.join(
                format_annotation(param, fully_qualified) for param in params))

        if not class_name:
            class_name = annotation_cls.__qualname__.title()

        return '{prefix}`{qualify}{module}.{name}`{extra}'.format(
            prefix=prefix,
            qualify="" if fully_qualified else "~",
            module=module,
            name=class_name,
            extra=extra
        )
    elif annotation is Ellipsis:
        return '...'
    elif (inspect.isfunction(annotation) and annotation.__module__ == 'typing' and
          hasattr(annotation, '__name__') and hasattr(annotation, '__supertype__')):
        return ':py:func:`{qualify}typing.NewType`\\(:py:data:`~{name}`, {extra})'.format(
            qualify="" if fully_qualified else "~",
            name=annotation.__name__,
            extra=format_annotation(annotation.__supertype__, fully_qualified),
        )
    elif inspect.isclass(annotation) or inspect.isclass(getattr(annotation, '__origin__', None)):
        if not inspect.isclass(annotation):
            annotation_cls = annotation.__origin__

        extra = ''
        mro = annotation_cls.mro()
        if Generic in mro or (Protocol and Protocol in mro):
            params = (getattr(annotation, '__parameters__', None) or
                      getattr(annotation, '__args__', None))
            if params:
                extra = '\\[{}]'.format(', '.join(
                    format_annotation(param, fully_qualified) for param in params))

        return ':py:class:`{qualify}{module}.{name}`{extra}'.format(
            qualify="" if fully_qualified else "~",
            module=annotation.__module__,
            name=annotation_cls.__qualname__,
            extra=extra
        )

    return str(annotation)


def process_signature(app, what: str, name: str, obj, options, signature, return_annotation):
    if not callable(obj):
        return

    if what in ('class', 'exception'):
        obj = getattr(obj, '__init__', getattr(obj, '__new__', None))

    if not getattr(obj, '__annotations__', None):
        return

    obj = inspect.unwrap(obj)
    signature = Signature(obj)
    parameters = [
        param.replace(annotation=inspect.Parameter.empty)
        for param in signature.signature.parameters.values()
    ]

    if '<locals>' in obj.__qualname__:
        logger.warning(
            'Cannot treat a function defined as a local function: "%s"  (use @functools.wraps)',
            name)
        return

    if parameters:
        if what in ('class', 'exception'):
            del parameters[0]
        elif what == 'method':
            outer = inspect.getmodule(obj)
            for clsname in obj.__qualname__.split('.')[:-1]:
                outer = getattr(outer, clsname)

            method_name = obj.__name__
            if method_name.startswith("__") and not method_name.endswith("__"):
                # If the method starts with double underscore (dunder)
                # Python applies mangling so we need to prepend the class name.
                # This doesn't happen if it always ends with double underscore.
                class_name = obj.__qualname__.split('.')[-2]
                method_name = "_{c}{m}".format(c=class_name, m=method_name)

            method_object = outer.__dict__[method_name] if outer else obj
            if not isinstance(method_object, (classmethod, staticmethod)):
                del parameters[0]

    signature.signature = signature.signature.replace(
        parameters=parameters,
        return_annotation=inspect.Signature.empty)

    return signature.format_args().replace('\\', '\\\\'), None


def get_all_type_hints(obj, name):
    rv = {}

    try:
        rv = get_type_hints(obj)
    except (AttributeError, TypeError):
        # Introspecting a slot wrapper will raise TypeError
        pass
    except NameError as exc:
        logger.warning('Cannot resolve forward reference in type annotations of "%s": %s',
                       name, exc)
        rv = obj.__annotations__

    if rv:
        return rv

    rv = backfill_type_hints(obj, name)

    try:
        obj.__annotations__ = rv
    except AttributeError:
        return rv

    try:
        rv = get_type_hints(obj)
    except (AttributeError, TypeError):
        pass
    except NameError as exc:
        logger.warning('Cannot resolve forward reference in type annotations of "%s": %s',
                       name, exc)
        rv = obj.__annotations__

    return rv


def backfill_type_hints(obj, name):
    rv = {}

    try:
        import typed_ast.ast3 as ast
    except ImportError:
        return rv

    def _one_child(module):
        children = list(ast.iter_child_nodes(module))

        if len(children) != 1:
            logger.warning(
                'Did not get exactly one node from AST for "%s", got %s', name, len(children))
            return

        return children[0]

    try:
        obj_ast = ast.parse(textwrap.dedent(inspect.getsource(obj)))
    except TypeError:
        return rv

    obj_ast = _one_child(obj_ast)
    if obj_ast is None:
        return rv

    try:
        type_comment = obj_ast.type_comment
    except AttributeError:
        return rv

    if not type_comment:
        return rv

    try:
        comment_args_str, comment_returns = type_comment.split(' -> ')
    except ValueError:
        logger.warning('Unparseable type hint comment for "%s": Expected to contain ` -> `', name)
        return rv

    if comment_returns:
        rv['return'] = comment_returns

    if comment_args_str not in ('()', '(...)'):
        logger.warning(
            'Only supporting `type: (...) -> rv`-style type hint comments, '
            'skipping types for "%s"', name
        )
        return rv

    try:
        args = list(ast.iter_child_nodes(obj_ast.args))
    except AttributeError:
        logger.warning('No args found on "%s"', name)
        return rv

    for arg in args:
        comment = getattr(arg, 'type_comment', None)
        if not comment:
            continue

        if not hasattr(arg, 'arg'):
            continue

        rv[arg.arg] = comment

    return rv


def process_docstring(app, what, name, obj, options, lines):
    if isinstance(obj, property):
        obj = obj.fget

    if callable(obj):
        if what in ('class', 'exception'):
            obj = getattr(obj, '__init__')

        obj = inspect.unwrap(obj)
        type_hints = get_all_type_hints(obj, name)

        for argname, annotation in type_hints.items():
            if argname.endswith('_'):
                argname = '{}\\_'.format(argname[:-1])

            formatted_annotation = format_annotation(
                annotation, fully_qualified=app.config.typehints_fully_qualified)

            if argname == 'return':
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

                if insert_index is not None:
                    if insert_index == len(lines):
                        # Ensure that :rtype: doesn't get joined with a paragraph of text, which
                        # prevents it being interpreted.
                        lines.append('')
                        insert_index += 1

                    lines.insert(insert_index, ':rtype: {}'.format(formatted_annotation))
            else:
                searchfor = ':param {}:'.format(argname)
                for i, line in enumerate(lines):
                    if line.startswith(searchfor):
                        lines.insert(i, ':type {}: {}'.format(argname, formatted_annotation))
                        break


def builder_ready(app):
    if app.config.set_type_checking_flag:
        typing.TYPE_CHECKING = True


def setup(app):
    app.add_config_value('set_type_checking_flag', False, 'html')
    app.add_config_value('typehints_fully_qualified', False, 'env')
    app.connect('builder-inited', builder_ready)
    app.connect('autodoc-process-signature', process_signature)
    app.connect('autodoc-process-docstring', process_docstring)
    return dict(parallel_read_safe=True)
