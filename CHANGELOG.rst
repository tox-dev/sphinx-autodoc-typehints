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
