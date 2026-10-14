"""Module with no type annotations, simulating a C extension."""


def greet(name, greeting):
    return f"{greeting}, {name}!"


class Calculator:
    value = 0

    def add(self, x):
        self.value += x
        return self

    class Inner:
        def process(self, data):
            return data


class Converter:
    """Convert output.

    :param output: the output format
    """

    def __new__(cls, output):
        instance = super().__new__(cls)
        instance.output = output
        return instance


async def fetch(url):
    return url


def transform(value):
    return value


def version_gated(value):
    return value


def overloaded(value):
    return value


def extras_only(value):
    return value


class Box:
    def __init__(self):
        self._size = 0

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

    @size.deleter
    def size(self):
        self._size = 0
