from typing import Any, Protocol, TypeVar

T = TypeVar("T")

class Model(Protocol):
    pass

class TextContent:
    text: str

class Types:
    TextContent: Any
    Model: Any
