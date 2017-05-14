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


How it works
------------

The extension listens to the ``autodoc-process-signature`` and ``autodoc-process-docstring``
Sphinx events. In the former, it strips the annotations from the function signature. In the latter,
it injects the appropriate ``:type argname:`` and ``:rtype:`` directives into the docstring.

Only arguments that have an existing ``:param:`` directive in the docstring get their respective
``:type:`` directives added. The ``:rtype:`` directive is added if and only if no existing
``:rtype:`` is found.

This extension does not currently have any configuration options.


Compatibility with sphinx.ext.napoleon
--------------------------------------

To use `sphinx.ext.napoleon`_ with sphinx-autodoc-typehints, make sure you load
`sphinx.ext.napoleon`_ first, **before** sphinx-autodoc-typehints. See `Issue 15`_ on the issue
tracker for more information.

.. _sphinx.ext.napoleon: http://www.sphinx-doc.org/en/stable/ext/napoleon.html
.. _Issue 15: https://github.com/agronholm/sphinx-autodoc-typehints/issues/15


Project links
-------------

* `Source repository <https://github.com/agronholm/sphinx-autodoc-typehints>`_
* `Issue tracker <https://github.com/agronholm/sphinx-autodoc-typehints/issues>`_
