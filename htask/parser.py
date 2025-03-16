from __future__ import annotations
from typing import Generic
from typing import Callable
from typing import TypeVar

from dataclasses import dataclass, field

import enum


Ty = TypeVar("Ty")


class ArgumentFormat(enum.StrEnum):
    STORE_VALUE = "store_value"
    STORE_TRUE = "store_true"
    STORE_FALSE = "store_false"


@dataclass
class ArgumentDescription(Generic[Ty]):
    dest: str
    switches: list[str]
    convert: Callable[[str], Ty]
    format: ArgumentFormat = field(default=ArgumentFormat.STORE_VALUE)
    default: Ty | None = field(default=None)
