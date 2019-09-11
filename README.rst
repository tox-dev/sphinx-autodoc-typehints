sphinx-autodoc-typehints
========================

This extension allows you to use Python 3 annotations for documenting acceptable argument types
and return value types of functions. This allows you to use type hints in a very natural fashion,
allowing you to migrate from this:

.. code-block:: python

    def format_unit(value, unit):
        """
        Formats the given value as a human readable string using the given units.

        :param float|int value: a numeric value
        :param str unit: the unit for the value (kg, m, etc.)
        :rtype: str
        """
        return '{} {}'.format(value, unit)

to this:

.. code-block:: python

    from typing import Union

    def format_unit(value: Union[float, int], unit: str) -> str:
        """
        Formats the given value as a human readable string using the given units.

        :param value: a numeric value
        :param unit: the unit for the value (kg, m, etc.)
        """
        return '{} {}'.format(value, unit)


Installation and setup
----------------------

First, use pip to download and install the extension::

    $ pip install sphinx-autodoc-typehints

Then, add the extension to your ``conf.py``:

.. code-block:: python

    extensions = [
        'sphinx.ext.autodoc',
        'sphinx_autodoc_typehints'
    ]


Options
-------

The following configuration options are accepted:

* ``set_type_checking_flag`` (default: ``False``): if ``True``, set ``typing.TYPE_CHECKING`` to
  ``True`` to enable "expensive" typing imports
* ``typehints_fully_qualified`` (default: ``False``): if ``True``, class names are always fully
  qualified (e.g. ``module.for.Class``). If ``False``, just the class name displays (e.g.
  ``Class``)
* ``always_document_param_types`` (default: ``False``): If ``False``, do not add type info for
  undocumented parameters.  If ``True``, add stub documentation for undocumented parameters to
  be able to add type info.


How it works
------------

The extension listens to the ``autodoc-process-signature`` and ``autodoc-process-docstring``
Sphinx events. In the former, it strips the annotations from the function signature. In the latter,
it injects the appropriate ``:type argname:`` and ``:rtype:`` directives into the docstring.

Only arguments that have an existing ``:param:`` directive in the docstring get their respective
``:type:`` directives added. The ``:rtype:`` directive is added if and only if no existing
``:rtype:`` is found.


Compatibility with sphinx.ext.napoleon
--------------------------------------

To use `sphinx.ext.napoleon`_ with sphinx-autodoc-typehints, make sure you load
`sphinx.ext.napoleon`_ first, **before** sphinx-autodoc-typehints. See `Issue 15`_ on the issue
tracker for more information.

.. _sphinx.ext.napoleon: http://www.sphinx-doc.org/en/stable/ext/napoleon.html
.. _Issue 15: https://github.com/agronholm/sphinx-autodoc-typehints/issues/15


Dealing with circular imports
-----------------------------

Sometimes functions or classes from two different modules need to reference each other in their
type annotations. This creates a circular import problem. The solution to this is the following:

#. Import only the module, not the classes/functions from it
#. Use forward references in the type annotations (e.g.
   ``def methodname(self, param1: 'othermodule.OtherClass'):``)

On Python 3.7, you can even use ``from __future__ import annotations`` and remove the quotes.


Using type hint comments
------------------------

If you're documenting code that needs to stay compatible with Python 2.7, you cannot use regular
type annotations. Instead, you must either be using Python 3.8 or later or have typed_ast_
installed. The package extras ``type_comments`` will pull in the appropiate dependencies automatically.
Then you can add type hint comments in the following manner:

.. code-block:: python

    def myfunction(arg1, arg2):
        # type: (int, str) -> int
        return 42

or alternatively:

.. code-block:: python

    def myfunction(
        arg1,  # type: int
        arg2  # type: str
    ):
        # type: (...) -> int
        return 42

.. _typed_ast: https://pypi.org/project/typed-ast/
