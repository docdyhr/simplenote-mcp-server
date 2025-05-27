from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

def fixture(
    scope: str = "function", params: Any = None, autouse: bool = False, ids: Any = None
) -> Callable[[Callable[..., T]], Callable[..., T]]: ...
