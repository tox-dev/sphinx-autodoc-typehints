from collections.abc import Callable, Sequence

type MyAlias = Callable[[str], str]

def greet(name: str, greeting: str) -> str: ...

class Calculator:
    value: int
    def add(self, x: int) -> Calculator: ...
    class Inner:
        def process(self, data: bytes) -> bytes: ...

class Converter:
    output: str
    def __new__(cls, output: str) -> Converter: ...  # ruff:ignore[non-self-return-type]

async def fetch(url: str) -> str: ...
def transform(value: Sequence[int]) -> list[str]: ...
