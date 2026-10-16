###########
 Tutorials
###########

This walk-through documents a small module from scratch, from installing the extension to reading the page it builds.
It assumes a Sphinx project, the ``docs`` folder :doc:`sphinx-quickstart <sphinx:man/sphinx-quickstart>` creates, next
to the code it documents.

****************************
 Document your first module
****************************

Install the extension
=====================

Install it from PyPI; it needs Python 3.12 or later and Sphinx 9.1 or later.

.. code-block:: bash

    python -m pip install sphinx-autodoc-typehints

Load it after autodoc
=====================

Add the extension to :confval:`extensions` in ``conf.py``, after :doc:`autodoc <sphinx:usage/extensions/autodoc>`,
the Sphinx extension that pulls documentation out of your code. An extension that rewrites docstrings, such as
:doc:`napoleon <sphinx:usage/extensions/napoleon>` or :doc:`numpydoc <numpydoc:index>`, goes between the two, see
:ref:`how-to:Use with napoleon` and :ref:`how-to:Use with numpydoc`.

.. code-block:: python

    # load autodoc first, then this extension
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]

Annotate the code
=================

Write the types once, as annotations, the ``value: float`` and ``-> str`` parts of a :pep:`484` signature, and leave
them out of the docstring. The docstring describes each parameter with a ``:param:`` :ref:`field
<sphinx:info-field-lists>` and names no type:

.. code-block:: python

    def format_unit(value: float, unit: str) -> str:
        """
        Format a value with its unit.

        :param value: a numeric value
        :param unit: the unit, such as kg or m
        """
        return f"{value} {unit}"

Point autodoc at it
===================

Save the code as ``mod.py`` where Python can import it while Sphinx runs, then let autodoc document the module from a
page of the docs, here ``index.rst``, with its :rst:dir:`automodule` directive:

.. code-block:: rst

    .. automodule:: mod
        :members:

Build and read the result
=========================

Build the docs with :doc:`sphinx-build <sphinx:man/sphinx-build>`:

.. code-block:: bash

    sphinx-build -b html docs docs/_build/html

Every example in these docs works this way, documenting a module ``mod`` with ``.. automodule:: mod`` and its
``:members:`` option. Each has four tabs, built while these docs were: *conf.py* holds the settings, *mod.py* the
source, *sphinx-autodoc-typehints* the page this extension renders, and *Sphinx built-in* the page Sphinx renders
without it, with ``autodoc_typehints = "description"``.

.. live-example::

    # load autodoc first, then this extension
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    def format_unit(value: float, unit: str) -> str:
        """
        Format a value with its unit.

        :param value: a numeric value
        :param unit: the unit, such as kg or m
        """
        return f"{value} {unit}"

The signature lists the parameter names alone. Each ``:param:`` field got the type of its annotation, and the return
annotation became a *Return type* field. Each type is a cross-reference: ``float`` and ``str`` link to the Python docs
because the examples load :doc:`intersphinx <sphinx:usage/extensions/intersphinx>`, the Sphinx extension that resolves
references against another project's docs. Without it, or without a mapping for the Python docs, they stay plain
text.

************
 Next steps
************

- Keep the types in the signature as well: :ref:`how-to:Choose where types appear`.
- Write Google or NumPy style docstrings: :ref:`how-to:Use with napoleon` and :ref:`how-to:Use with numpydoc`.
- Add a field for every parameter, documented or not: :ref:`how-to:Document every parameter`.
- Show the default values next to the types: :ref:`how-to:Show default values`.
- See what the extension adds to Sphinx's own type hints: :ref:`concepts:Compared with Sphinx's built-in type hints`.
- Look up an option: :ref:`reference:Configuration options`.
