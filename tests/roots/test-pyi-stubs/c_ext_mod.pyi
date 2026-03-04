from collections.abc import Callable, Sequence
from typing import Any, Self

type GreetHook = Callable[[str], Any]
type EncoderHook = Callable[[Any], Any]

def greet(name: str, greeting: Sequence[str]) -> str: ...
def with_hook(callback: GreetHook) -> None: ...

class Encoder:
    def __new__(cls, default: EncoderHook | None = None) -> Self: ...
