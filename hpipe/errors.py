from __future__ import annotations
from typing import Sequence
from typing import Set
from typing import TYPE_CHECKING

from dataclasses import dataclass

if TYPE_CHECKING:
    from hpipe.pipeline import Job

__all__ = ("JobFailed", "StageIsNotDefined", "StagesAreAlreadyDefined")


class JobFailed(Exception): ...


@dataclass
class JobRequiredCommandNotFound(Exception):
    missing: Sequence[str]
    required: Sequence[str]

    def __post_init__(self):
        super().__init__(
            f"Missing commands: {self.missing}. Required: {self.required}."
        )

@dataclass
class PipelineMissingRequiredPrograms(Exception):
    missing: dict[Job, list[str]]
    
    def __post_init__(self):
        super().__init__(
            f"Missing commands: {self.missing}"
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
    job: Job
    defined_stages: Sequence[str]

    def __post_init__(self):
        super().__init__(
            f"Stage doesn't defined: {self.job.stage!r}, stages={self.defined_stages!r}. Referenced from job={self.job!r}"
        )


# @dataclass
# class StageCantBeNone(Exception):
#     job: Job
#     defined_stages: Pipeline
#
#     def __post_init__(self):
#         super().__init__(
#             f"Stage can't be None: pipeline={self.pipeline!r}. Referenced from job={self.job!r}"
#         )


@dataclass
class StagesAreAlreadyDefined(Exception):
    duplacated_stages: Set[str]
    defined_stages: Sequence[str]

    def __post_init__(self):
        super().__init__(
            f"Stages is already defined: {self.duplacated_stages!r}, stages={self.defined_stages!r}"
        )
