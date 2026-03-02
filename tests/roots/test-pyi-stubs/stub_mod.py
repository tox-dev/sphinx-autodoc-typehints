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


async def fetch(url):
    return url


def transform(value):
    return value
