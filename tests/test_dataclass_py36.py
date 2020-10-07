import pathlib
import sys
import textwrap

import pytest


@pytest.mark.parametrize('always_document_param_types', [True, False])
@pytest.mark.sphinx('text', testroot='dataclass')
def test_sphinx_output(app, status, warning, always_document_param_types):
    test_path = pathlib.Path(__file__).parent

    # Add test directory to sys.path to allow imports of dummy module.
    if str(test_path) not in sys.path:
        sys.path.insert(0, str(test_path))

    app.config.always_document_param_types = always_document_param_types
    app.build()

    assert 'build succeeded' in status.getvalue()  # Build succeeded

    format_args = {}
    if always_document_param_types:
        for indentation_level in range(3):
            format_args['undoc_params_{}'.format(indentation_level)] = textwrap.indent(
                '\n\n   Parameters:\n      **x** ("int") --', '   ' * indentation_level
            )
    else:
        for indentation_level in range(3):
            format_args['undoc_params_{}'.format(indentation_level)] = ''

    text_path = pathlib.Path(app.srcdir) / '_build' / 'text' / 'index.txt'
    with text_path.open('r') as f:
        text_contents = f.read().replace('–', '--')
        expected_contents = textwrap.dedent('''\
        Dataclass Module
        ****************

        class dataclass_module.DataClass(x)

           Class docstring.{undoc_params_0}

           __init__(x)

              Initialize self.  See help(type(self)) for accurate signature.{undoc_params_1}
        ''')
        expected_contents = expected_contents.format(**format_args).replace('–', '--')
        assert text_contents == expected_contents
