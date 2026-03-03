from collections.abc import Callable, Sequence
from typing import Any

type GreetHook = Callable[[str], Any]

def greet(name: str, greeting: Sequence[str]) -> str: ...
def with_hook(callback: GreetHook) -> None: ...
