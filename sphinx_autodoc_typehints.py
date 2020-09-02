import inspect
import sys
import textwrap
import typing
from typing import get_type_hints, TypeVar, Any, AnyStr, Tuple

from sphinx.util import logging
from sphinx.util.inspect import signature as Signature
from sphinx.util.inspect import stringify_signature

logger = logging.getLogger(__name__)
pydata_annotations = {'Any', 'AnyStr', 'Callable', 'ClassVar', 'Literal', 'NoReturn', 'Optional',
                      'Tuple', 'Union'}


def get_annotation_module(annotation) -> str:
    # Special cases
    if annotation is None:
        return 'builtins'

    if hasattr(annotation, '__module__'):
        return annotation.__module__

    if hasattr(annotation, '__origin__'):
        return annotation.__origin__.__module__

    raise ValueError('Cannot determine the module of {}'.format(annotation))


def get_annotation_class_name(annotation, module: str) -> str:
    # Special cases
    if annotation is None:
        return 'None'
    elif annotation is Any:
        return 'Any'
    elif annotation is AnyStr:
        return 'AnyStr'
    elif inspect.isfunction(annotation) and hasattr(annotation, '__supertype__'):
        return 'NewType'

    if getattr(annotation, '__qualname__', None):
        return annotation.__qualname__
    elif getattr(annotation, '_name', None):  # Required for generic aliases on Python 3.7+
        return annotation._name
    elif (module in ('typing', 'typing_extensions')
            and isinstance(getattr(annotation, 'name', None), str)):
        # Required for at least Pattern and Match
        return annotation.name

    origin = getattr(annotation, '__origin__', None)
    if origin:
        if getattr(origin, '__qualname__', None):  # Required for Protocol subclasses
            return origin.__qualname__
        elif getattr(origin, '_name', None):  # Required for Union on Python 3.7+
            return origin._name
        else:
            return origin.__class__.__qualname__.lstrip('_')  # Required for Union on Python < 3.7

    annotation_cls = annotation if inspect.isclass(annotation) else annotation.__class__
    return annotation_cls.__qualname__.lstrip('_')


def get_annotation_args(annotation, module: str, class_name: str) -> Tuple:
    try:
        original = getattr(sys.modules[module], class_name)
    except (KeyError, AttributeError):
        pass
    else:
        if annotation is original:
            return ()  # This is the original, unparametrized type

    # Special cases
    if class_name in ('Pattern', 'Match') and hasattr(annotation, 'type_var'):  # Python < 3.7
        return annotation.type_var,
    elif class_name == 'Callable' and hasattr(annotation, '__result__'):  # Python < 3.5.3
        argtypes = (Ellipsis,) if annotation.__args__ is Ellipsis else annotation.__args__
        return argtypes + (annotation.__result__,)
    elif class_name == 'Union' and hasattr(annotation, '__union_params__'):  # Union on Python 3.5
        return annotation.__union_params__
    elif class_name == 'Tuple' and hasattr(annotation, '__tuple_params__'):  # Tuple on Python 3.5
        params = annotation.__tuple_params__
        if getattr(annotation, '__tuple_use_ellipsis__', False):
            params += (Ellipsis,)

        return params
    elif class_name == 'ClassVar' and hasattr(annotation, '__type__'):  # ClassVar on Python < 3.7
        return annotation.__type__,
    elif class_name == 'NewType' and hasattr(annotation, '__supertype__'):
        return annotation.__supertype__,
    elif class_name == 'Literal' and hasattr(annotation, '__values__'):
        return annotation.__values__
    elif class_name == 'Generic':
        return annotation.__parameters__

    return getattr(annotation, '__args__', ())


def format_annotation(annotation, fully_qualified: bool = False) -> str:
    # Special cases
    if annotation is None or annotation is type(None):  # noqa: E721
        return ':py:obj:`None`'
    elif annotation is Ellipsis:
        return '...'

    # Type variables are also handled specially
    try:
        if isinstance(annotation, TypeVar) and annotation is not AnyStr:
            return '\\' + repr(annotation)
    except TypeError:
        pass

    try:
        module = get_annotation_module(annotation)
        class_name = get_annotation_class_name(annotation, module)
        args = get_annotation_args(annotation, module, class_name)
    except ValueError:
        return str(annotation)

    # Redirect all typing_extensions types to the stdlib typing module
    if module == 'typing_extensions':
        module = 'typing'

    full_name = (module + '.' + class_name) if module != 'builtins' else class_name
    prefix = '' if fully_qualified or full_name == class_name else '~'
    role = 'data' if class_name in pydata_annotations else 'class'
    args_format = '\\[{}]'
    formatted_args = ''

    # Some types require special handling
    if full_name == 'typing.NewType':
        args_format = '\\(:py:data:`~{name}`, {{}})'.format(name=annotation.__name__)
        role = 'func'
    elif full_name == 'typing.Union' and len(args) == 2 and type(None) in args:
        full_name = 'typing.Optional'
        args = tuple(x for x in args if x is not type(None))  # noqa: E721
    elif full_name == 'typing.Callable' and args and args[0] is not ...:
        formatted_args = '\\[\\[' + ', '.join(format_annotation(arg) for arg in args[:-1]) + ']'
        formatted_args += ', ' + format_annotation(args[-1]) + ']'
    elif full_name == 'typing.Literal':
        formatted_args = '\\[' + ', '.join(repr(arg) for arg in args) + ']'

    if args and not formatted_args:
        formatted_args = args_format.format(', '.join(format_annotation(arg, fully_qualified)
                                                      for arg in args))

    return ':py:{role}:`{prefix}{full_name}`{formatted_args}'.format(
        role=role, prefix=prefix, full_name=full_name, formatted_args=formatted_args)


def process_signature(app, what: str, name: str, obj, options, signature, return_annotation):
    if not callable(obj):
        return

    original_obj = obj
    if inspect.isclass(obj):
        obj = getattr(obj, '__init__', getattr(obj, '__new__', None))

    if not getattr(obj, '__annotations__', None):
        return

    obj = inspect.unwrap(obj)
    signature = Signature(obj)
    parameters = [
        param.replace(annotation=inspect.Parameter.empty)
        for param in signature.parameters.values()
    ]

    # The generated dataclass __init__() and class are weird and need extra checks
    # This helper function operates on the generated class and methods
    # of a dataclass, not an instantiated dataclass object. As such,
    # it cannot be replaced by a call to `dataclasses.is_dataclass()`.
    def _is_dataclass(name: str, what: str, qualname: str) -> bool:
        if what == 'method' and name.endswith('.__init__'):
            # generated __init__()
            return True
        if what == 'class' and qualname.endswith('.__init__'):
            # generated class
            return True
        return False

    if '<locals>' in obj.__qualname__ and not _is_dataclass(name, what, obj.__qualname__):
        logger.warning(
            'Cannot treat a function defined as a local function: "%s"  (use @functools.wraps)',
            name)
        return

    if parameters:
        if inspect.isclass(original_obj) or (what == 'method' and name.endswith('.__init__')):
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

    signature = signature.replace(
        parameters=parameters,
        return_annotation=inspect.Signature.empty)

    return stringify_signature(signature).replace('\\', '\\\\'), None


def get_all_type_hints(obj, name):
    rv = {}

    try:
        rv = get_type_hints(obj)
    except (AttributeError, TypeError, RecursionError):
        # Introspecting a slot wrapper will raise TypeError, and and some recursive type
        # definitions will cause a RecursionError (https://github.com/python/typing/issues/574).
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
    except (AttributeError, TypeError):
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
    parse_kwargs = {}
    if sys.version_info < (3, 8):
        try:
            import typed_ast.ast3 as ast
        except ImportError:
            return {}
    else:
        import ast
        parse_kwargs = {'type_comments': True}

    def _one_child(module):
        children = module.body  # use the body to ignore type comments

        if len(children) != 1:
            logger.warning(
                'Did not get exactly one node from AST for "%s", got %s', name, len(children))
            return

        return children[0]

    try:
        obj_ast = ast.parse(textwrap.dedent(inspect.getsource(obj)), **parse_kwargs)
    except (OSError, TypeError):
        return {}

    obj_ast = _one_child(obj_ast)
    if obj_ast is None:
        return {}

    try:
        type_comment = obj_ast.type_comment
    except AttributeError:
        return {}

    if not type_comment:
        return {}

    try:
        comment_args_str, comment_returns = type_comment.split(' -> ')
    except ValueError:
        logger.warning('Unparseable type hint comment for "%s": Expected to contain ` -> `', name)
        return {}

    rv = {}
    if comment_returns:
        rv['return'] = comment_returns

    args = load_args(obj_ast)
    comment_args = split_type_comment_args(comment_args_str)
    is_inline = len(comment_args) == 1 and comment_args[0] == "..."
    if not is_inline:
        if args and args[0].arg in ("self", "cls") and len(comment_args) != len(args):
            comment_args.insert(0, None)  # self/cls may be omitted in type comments, insert blank

        if len(args) != len(comment_args):
            logger.warning('Not enough type comments found on "%s"', name)
            return rv

    for at, arg in enumerate(args):
        arg_key = getattr(arg, "arg", None)
        if arg_key is None:
            continue

        if is_inline:  # the type information now is tied to the argument
            value = getattr(arg, "type_comment", None)
        else:  # type data from comment
            value = comment_args[at]

        if value is not None:
            rv[arg_key] = value

    return rv


def load_args(obj_ast):
    func_args = obj_ast.args
    args = []
    pos_only = getattr(func_args, 'posonlyargs', None)
    if pos_only:
        args.extend(pos_only)

    args.extend(func_args.args)
    if func_args.vararg:
        args.append(func_args.vararg)

    args.extend(func_args.kwonlyargs)
    if func_args.kwarg:
        args.append(func_args.kwarg)

    return args


def split_type_comment_args(comment):
    def add(val):
        result.append(val.strip().lstrip("*"))  # remove spaces, and var/kw arg marker

    comment = comment.strip().lstrip("(").rstrip(")")
    result = []
    if not comment:
        return result

    brackets, start_arg_at, at = 0, 0, 0
    for at, char in enumerate(comment):
        if char in ("[", "("):
            brackets += 1
        elif char in ("]", ")"):
            brackets -= 1
        elif char == "," and brackets == 0:
            add(comment[start_arg_at:at])
            start_arg_at = at + 1

    add(comment[start_arg_at: at + 1])
    return result


def process_docstring(app, what, name, obj, options, lines):
    original_obj = obj
    if isinstance(obj, property):
        obj = obj.fget

    if callable(obj):
        if inspect.isclass(obj):
            obj = getattr(obj, '__init__')

        obj = inspect.unwrap(obj)
        type_hints = get_all_type_hints(obj, name)

        for argname, annotation in type_hints.items():
            if argname == 'return':
                continue  # this is handled separately later
            if argname.endswith('_'):
                argname = '{}\\_'.format(argname[:-1])

            formatted_annotation = format_annotation(
                annotation, fully_qualified=app.config.typehints_fully_qualified)

            searchfor = [':{} {}:'.format(field, argname)
                         for field in ('param', 'parameter', 'arg', 'argument')]
            insert_index = None

            for i, line in enumerate(lines):
                if any(line.startswith(search_string) for search_string in searchfor):
                    insert_index = i
                    break

            if insert_index is None and app.config.always_document_param_types:
                lines.append(':param {}:'.format(argname))
                insert_index = len(lines)

            if insert_index is not None:
                lines.insert(
                    insert_index,
                    ':type {}: {}'.format(argname, formatted_annotation)
                )

        if 'return' in type_hints and not inspect.isclass(original_obj):
            # This avoids adding a return type for data class __init__ methods
            if what == 'method' and name.endswith('.__init__'):
                return

            formatted_annotation = format_annotation(
                type_hints['return'], fully_qualified=app.config.typehints_fully_qualified)

            insert_index = len(lines)
            for i, line in enumerate(lines):
                if line.startswith(':rtype:'):
                    insert_index = None
                    break
                elif line.startswith(':return:') or line.startswith(':returns:'):
                    insert_index = i

            if insert_index is not None and app.config.typehints_document_rtype:
                if insert_index == len(lines):
                    # Ensure that :rtype: doesn't get joined with a paragraph of text, which
                    # prevents it being interpreted.
                    lines.append('')
                    insert_index += 1

                lines.insert(insert_index, ':rtype: {}'.format(formatted_annotation))


def builder_ready(app):
    if app.config.set_type_checking_flag:
        typing.TYPE_CHECKING = True


def setup(app):
    app.add_config_value('set_type_checking_flag', False, 'html')
    app.add_config_value('always_document_param_types', False, 'html')
    app.add_config_value('typehints_fully_qualified', False, 'env')
    app.add_config_value('typehints_document_rtype', True, 'env')
    app.connect('builder-inited', builder_ready)
    app.connect('autodoc-process-signature', process_signature)
    app.connect('autodoc-process-docstring', process_docstring)
    return dict(parallel_read_safe=True)
