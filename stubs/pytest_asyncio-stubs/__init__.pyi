from typing import Any, Callable, TypeVar

T = TypeVar("T")

def fixture(
    scope: str = "function", params: Any = None, autouse: bool = False, ids: Any = None
) -> Callable[[Callable[..., T]], Callable[..., T]]: ...
