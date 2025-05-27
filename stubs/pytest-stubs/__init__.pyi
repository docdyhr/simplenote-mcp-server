from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

class FixtureRequest:
    param: Any
    def getfixturevalue(self, name: str) -> Any: ...

# Simple version compatible with Python 3.11 and 3.13
def fixture(
    scope: str = "function",
    params: list[Any] | None = None,
    autouse: bool = False,
    ids: list[str] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]: ...
def mark() -> Mark: ...

class Mark:
    def parametrize(
        self,
        argnames: str | list[str],
        argvalues: list[Any],
        ids: list[str] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    def skip(
        self, reason: str = ""
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    def skipif(
        self, condition: bool, reason: str = ""
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    def xfail(
        self, condition: bool = True, reason: str = ""
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    def asyncio(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...

class MonkeyPatch:
    def setattr(self, target: Any, name: str, value: Any) -> None: ...
    def setenv(self, name: str, value: str) -> None: ...
    def delenv(self, name: str) -> None: ...
    def syspath_prepend(self, path: str) -> None: ...

raises = Any  # For contextlib integration, type too complex for stub

def fail(msg: str = "") -> None: ...
