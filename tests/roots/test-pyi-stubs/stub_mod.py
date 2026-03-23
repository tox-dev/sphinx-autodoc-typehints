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
