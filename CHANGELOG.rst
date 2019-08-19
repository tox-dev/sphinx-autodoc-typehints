1.7.0
=====

* Dropped support for Python 3.4
* Fixed unwrapped local functions causing errors (PR by Kimiyuki Onaka)
* Fixed ``AttributeError`` when documenting the ``__init__()`` method of a data class
* Added support for type hint comments (PR by Markus Unterwaditzer)
* Added flag for rendering classes with their fully qualified names (PR by Holly Becker)


1.6.0
=====

* Fixed ``TypeError`` when formatting annotations from a class that inherits from a concrete
  generic type (report and tests by bpeake-illuscio)
* Added support for ``typing_extensions.Protocol`` (PR by Ian Good)
* Added support for ``typing.NewType`` (PR by George Leslie-Waksman)


1.5.2
=====

* Emit a warning instead of crashing when an unresolvable forward reference is encountered in type
  annotations


1.5.1
=====

* Fixed escape characters in parameter default values getting lost during signature processing
* Replaced use of the ``config-inited`` event (which inadvertently required Sphinx 1.8) with the
  ``builder-inited`` event


1.5.0
=====

* The setting of the ``typing.TYPECHECKING`` flag is now configurable using the
  ``set_type_checking_flag`` option


1.4.0
=====

* The extension now sets ``typing.TYPECHECKING`` to ``True`` during setup to include conditional
  imports which may be used in type annotations
* Fixed parameters with trailing underscores (PR by Daniel Knell)
* Fixed KeyError with private methods (PR by Benito Palacios Sánchez)
* Fixed deprecation warning about the use of formatargspec (PR by Y. Somda)
* The minimum Sphinx version is now v1.7.0


1.3.1
=====

* Fixed rendering of generic types outside the typing module (thanks to Tim Poterba for the PR)


1.3.0
=====

* Fixed crash when processing docstrings from nested classes (thanks to dilyanpalauzov for the fix)
* Added support for Python 3.7
* Dropped support for Python 3.5.0 and 3.5.1


1.2.5
=====

* Ensured that ``:rtype:`` doesn't get joined with a paragraph of text
  (thanks to Bruce Merry for the PR)


1.2.4
=====

* Removed support for ``backports.typing`` as it has been removed from the PyPI
* Fixed first parameter being cut out from class methods and static methods
  (thanks to Josiah Wolf Oberholtzer for the PR)


1.2.3
=====

* Fixed `process_signature()` clobbering any explicitly overridden signatures from the docstring


1.2.2
=====

* Explicitly prefix ``:class:``, ``:mod:`` et al with ``:py:``, in case ``py`` is not the default
  domain of the project (thanks Monty Taylor)


1.2.1
=====

* Fixed `ValueError` when `getargspec()` encounters a built-in function
* Fixed `AttributeError` when `Any` is combined with another type in a `Union`
  (thanks Davis Kirkendall)


1.2.0
=====

* Fixed compatibility with Python 3.6 and 3.5.3
* Fixed ``NameError`` when processing signatures of wrapped functions with type hints
* Fixed handling of slotted classes with no ``__init__()`` method
* Fixed Sphinx warning about parallel reads
* Fixed return type being added to class docstring from its ``__init__()`` method
  (thanks to Manuel Krebber for the patch)
* Fixed return type hints of ``@property`` methods being omitted (thanks to pknight for the patch)
* Added a test suite (thanks Manuel Krebber)


1.1.0
=====

* Added proper support for ``typing.Tuple`` (pull request by Manuel Krebber)


1.0.6
=====

* Fixed wrong placement of ``:rtype:`` if a multi-line ``:param:`` or a ``:returns:`` is used


1.0.5
=====

* Fixed coroutine functions' signatures not being processed when using sphinxcontrib-asyncio


1.0.4
=====

* Fixed compatibility with Sphinx 1.4


1.0.3
=====

* Fixed "self" parameter not being removed from exception class constructor signatures
* Fixed process_signature() erroneously removing the first argument of a static method


1.0.2
=====

* Fixed exception classes not being processed like normal classes


1.0.1
=====

* Fixed errors caused by forward references not being looked up with the right globals


1.0.0
=====

* Initial release
