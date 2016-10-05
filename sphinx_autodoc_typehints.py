import inspect
import sys

from sphinx.util.inspect import getargspec
from sphinx.ext.autodoc import formatargspec

try:
    from backports.typing import (Any, Callable, Generic, GenericMeta, Tuple, TypeVar, TypingMeta,
                                  Union, _ForwardRef, _TypeAlias, get_type_hints)
except ImportError:
    from typing import (Any, Callable, Generic, GenericMeta, Tuple, TypeVar, TypingMeta,
                        Union, _ForwardRef, _TypeAlias, get_type_hints)

try:
    from typing import ClassVar
except ImportError:
    ClassVar = None

    
def format_annotation(annotation, obj=None):
    if isinstance(annotation, type):
        qname = sys.version_info[:2] >= (3, 3) and annotation.__qualname__ or annotation.__name__

        # builtin types don't need to be qualified with a module name
        if annotation.__module__ == 'builtins':
            if qname == 'NoneType':
                return '``None``'
            else:
                return ':class:`%s`' % qname

        params = None

        # Check first if we have an TypingMeta instance, because when mixing in another meta class,
        # some informatiion might get lost.
        # For example, a class inheriting from both tuple and Enum ends up not having the TypingMeta
        # metaclass and hence none of the Tuple typing information.
        if isinstance(annotation, TypingMeta):
            # Since Any is a superclass of everything, make sure it gets handled normally.
            if annotation is Any:
                pass 

            # Generic classes have type arguments
            elif isinstance(annotation, GenericMeta):
                params = annotation.__args__
                
                # Make sure to format Generic[T, U, ...] correctly, because it only
                # has parameters but nor argument values for them
                if not params and issubclass(annotation, Generic):
                    params = annotation.__parameters__

            # Tuples are not Generics, so handle their type parameters separately.
            elif issubclass(annotation, Tuple):
                if annotation.__tuple_params__:
                    params = list(annotation.__tuple_params__)
                # Tuples can have variable size with a fixed type, indicated by an Ellipsis: Tuple[T, ...].
                if annotation.__tuple_use_ellipsis__:
                    if params is None:
                        params = []
                    params.append(Ellipsis)

            # Unions are not Generics, so handle their type parameters separately.
            elif issubclass(annotation, Union):
                if annotation.__union_params__:
                    params = list(annotation.__union_params__)
                    # If the Union contains None, wrap it in an Optional, i.e.
                    # Union[T,None]   => Optional[T]
                    # Union[T,U,None] => Optional[Union[T, U]]
                    if annotation.__union_set_params__ and type(None) in annotation.__union_set_params__:
                        qname = 'Optional'
                        params.remove(type(None))
                        if len(params) > 1:
                            params = [Union[tuple(params)]]

            # Callables are not Generics, so handle their type parameters separately.
            # They have the format Callable[arg_types, return_type].
            # arg_types is either a list of types or an Ellipsis for Callables with variable arguments.
            elif issubclass(annotation, Callable):
                if annotation.__args__ is not None or annotation.__result__ is not None:
                    if annotation.__args__ is Ellipsis:
                        args_r = Ellipsis
                    else:
                        args_r = '\\[%s]' % ', '.join(format_annotation(a, obj) for a in annotation.__args__)

                    params = [args_r, annotation.__result__]

            # Type variables are formatted with a prefix character (~, +, -) which has to be escaped.
            elif isinstance(annotation, TypeVar):
                return '\\' + repr(annotation)

            # Strings inside of type annotations are converted to _ForwardRef internally
            elif isinstance(annotation, _ForwardRef):
                try:
                    try:
                        global_vars = obj is not None and obj.__globals__
                    except AttributeError:
                        global_vars = None
                    # Evaluate the type annotation string and then format it
                    actual_type = eval(annotation.__forward_arg__, global_vars) # pylint: disable=eval-used
                    return format_annotation(actual_type, obj)
                except SyntaxError:
                    return annotation.__forward_arg__

            # ClassVar is just a wrapper for another type to indicate it annotates a class variable.
            elif ClassVar and issubclass(annotation, ClassVar):
                return format_annotation(annotation.__type__, obj)

        generic = params and '\\[%s]' % ', '.join(format_annotation(p, obj) for p in params) or ''
        return ':class:`~%s.%s`%s' % (annotation.__module__, qname, generic)
    
    # _TypeAlias is an internal class used for the Pattern/Match types
    # It represents an alias for another type, e.g. Pattern is an alias for any string type
    elif isinstance(annotation, _TypeAlias):
        return ':class:`~typing.%s`\\[%s]' % (annotation.name, format_annotation(annotation.type_var, obj))

    # Ellipsis is used in Callable/Tuple
    elif annotation is Ellipsis:
        return '...'

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
            formatted_annotation = format_annotation(annotation, obj)

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
