from typing import Sequence
from typing import Set

from dataclasses import dataclass

__all__ = ("JobFailed", "StageIsNotDefined", "StagesAreAlreadyDefined")


class JobFailed(Exception): ...


@dataclass
class JobRequiredCommandNotFound(Exception):
    missing: Sequence[str]
    required: Sequence[str]

    def __post_init__(self):
        super().__init__(
            f"Missing commands: {self.missing}. Required: {self.required}"
        )


@dataclass
class JobCommandFailed(Exception):
    command: str
    returncode: int

    def __post_init__(self):
        super().__init__(
            f"{self.command!r} command failed and exited with {self.returncode} return code"
        )


@dataclass
class StageIsNotDefined(Exception):
    stage: str
    defined_stages: Sequence[str]

    def __post_init__(self):
        super().__init__(
            f"Stage doesn't defined: {self.stage!r}, stages={self.defined_stages!r}"
        )


@dataclass
class StagesAreAlreadyDefined(Exception):
    duplacated_stages: Set[str]
    defined_stages: Sequence[str]

    def __post_init__(self):
        super().__init__(
            f"Stages is already defined: {self.duplacated_stages!r}, stages={self.defined_stages!r}"
        )
