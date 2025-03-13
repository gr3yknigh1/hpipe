from __future__ import annotations
from typing import TypeVar
from typing import Callable
from typing import Set

import sys

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

_ParamsType = ParamSpec("_ParamsType")
_ReturnType = TypeVar("_ReturnType")

__all__ = ("AlreadyCalledError", "require_call_once")

class AlreadyCalledError(Exception): ...

_already_called: Set[Callable] = set()

def require_call_once(*, error_message: str):
    def internal(
        func: Callable[_ParamsType, _ReturnType],
    ) -> Callable[_ParamsType, _ReturnType]:
        def wrapper(
            *args: _ParamsType.args, **kwargs: _ParamsType.kwargs
        ) -> _ReturnType:
            global _already_called
            if func in _already_called:
                raise AlreadyCalledError(f"{func.__name__}(): {error_message}")
            _already_called.add(func)

            return func(*args, **kwargs)

        return wrapper

    return internal
