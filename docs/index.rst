##########################
 sphinx-autodoc-typehints
##########################

This `Sphinx <https://www.sphinx-doc.org/>`_ extension reads the :mod:`type hints <typing>` of the code
:doc:`autodoc <sphinx:usage/extensions/autodoc>` documents and writes them into the parameter and return fields, so you
state each type once, in the code:

.. code-block:: python

    # conf.py: load autodoc first, then this extension
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]

Sphinx's own :confval:`autodoc_typehints = "description" <autodoc_typehints>` also moves types into the fields. On top
of it, this extension links names your code imports only for type checkers, inside an :data:`if TYPE_CHECKING:
<typing.TYPE_CHECKING>` block, and reads types from ``.pyi`` stub files, which hold the annotations of a module whose
code has none. It documents the :func:`@overload <typing.overload>` variants a function declares for type checkers,
default values, the keys of ``**kwargs``, and docstrings written for :doc:`numpydoc <numpydoc:index>`.
:ref:`concepts:Compared with Sphinx's built-in type hints` lists the differences, and the :doc:`changelog` lists the
changes in each version.

**************
 Installation
**************

``sphinx-autodoc-typehints`` is available on PyPI. It needs Python 3.12 or later and Sphinx 9.1 or later:

.. code-block:: bash

    python -m pip install sphinx-autodoc-typehints

Parallel builds, ``sphinx-build -j``, work with the extension loaded.

********************************
 Learn sphinx-autodoc-typehints
********************************

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card::

        **New to the extension?**

        Start with the :doc:`tutorials` to document a first annotated module.

    .. grid-item-card::

        **Have a specific task?**

        Each of the :doc:`how-to` changes one thing about the output, such as where types appear or how defaults show.

    .. grid-item-card::

        **Looking up an option?**

        The :doc:`reference` lists the configuration options, the warnings and how each typing construct renders.

    .. grid-item-card::

        **Want to know how it works?**

        :doc:`concepts` follows a type from the annotation to the rendered page.

**********
 Features
**********

.. grid:: 1 2 2 3
    :gutter: 2

    .. grid-item-card::
        **Types in the fields**

        Parameter and return types go below the signature, or stay in it.

        - :ref:`how-to:Choose where types appear`
        - :ref:`how-to:Show default values`
        - :ref:`how-to:Control return types`

    .. grid-item-card::
        **Every docstring style**

        Sphinx's ``:param:`` fields, Google or NumPy sections through napoleon, or numpydoc's sections.

        - :ref:`how-to:Use with napoleon`
        - :ref:`how-to:Use with numpydoc`

    .. grid-item-card::
        **Types that resolve**

        A name imported only for type checkers, or declared in a ``.pyi`` stub, links like any other.

        - :ref:`type-checking`
        - :ref:`pyi-stubs`

    .. grid-item-card::
        **Linked types**

        Every part of a type links to its documentation, type aliases included.

        - :ref:`how-to:Link type aliases`
        - :ref:`how-to:Fix standard library cross-references`

    .. grid-item-card::
        **Overloads and kwargs**

        Each :func:`@overload <typing.overload>` variant, and each keyword argument a :class:`~typing.TypedDict` types.

        - :ref:`how-to:Document overloads`
        - :ref:`kwargs-unpack`

    .. grid-item-card::
        **Objects beyond functions**

        Notices for deprecated objects, links to overridden methods, and the types of attributes and setters.

        - :ref:`reference:Object features`

.. toctree::
    :hidden:

    self
    tutorials
    how-to
    reference
    typing
    concepts
    changelog
    license
