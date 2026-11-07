"""
Rendering turns resolved types into reST cross-reference markup for docstring fields and signatures.

It sits beside `_resolve` and imports nothing from it; `_documented` hands in what it needs from resolution, such as
the guard binder.
"""
