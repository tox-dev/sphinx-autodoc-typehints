import os.path

from setuptools import setup

here = os.path.dirname(__file__)
readme_path = os.path.join(here, 'README.rst')
readme = open(readme_path).read()

setup(
    name='sphinx-autodoc-typehints',
    use_scm_version=True,
    description='Type hints (PEP 484) support for the Sphinx autodoc extension',
    long_description=readme,
    author='Alex Grönholm',
    author_email='alex.gronholm@nextday.fi',
    url='https://github.com/agronholm/sphinx-autodoc-typehints',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Sphinx :: Extension',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Framework :: Sphinx :: Extension',
        'Topic :: Documentation :: Sphinx',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    license='MIT',
    zip_safe=True,
    py_modules=['sphinx_autodoc_typehints'],
    setup_requires=[
        'setuptools_scm >= 1.7.0'
    ],
    install_requires=[
        'Sphinx >= 1.4'
    ],
    extras_require={
        ':python_version == "3.3"': 'typing >= 3.5',
        ':python_version == "3.4"': 'typing >= 3.5'
    }
)
