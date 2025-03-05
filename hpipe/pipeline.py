from typing import Callable
from typing import List
from typing import TypeVar
from typing import Set
from typing import Optional
from typing import Sequence

import sys

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from logging import getLogger
from abc import ABC
from abc import abstractmethod
import subprocess
import shlex
import shutil

from hpipe import errors

__all__ = ("Pipeline", "Job")

_ParamsType = ParamSpec("_ParamsType")
_ReturnType = TypeVar("_ReturnType")

JobHandler = Callable[["Job"], None]


logger = getLogger("pipeline")


class Shell(ABC):
    @abstractmethod
    def execute(self, command: str, *, timeout: Optional[float]) -> int:
        raise NotImplementedError()


class Bash(Shell):
    def execute(self, command: str, *, timeout: Optional[float] = None) -> int:
        command_wrapper = f"bash -c '{command}'"

        print()
        proc = subprocess.Popen(args=shlex.split(command_wrapper))
        proc.wait(timeout=timeout)
        print()

        return proc.returncode


@dataclass
class Job:
    stage: str
    handler: JobHandler = field(repr=False)

    required_commands: Sequence[str]

    dry_run: bool = field(default=False)

    def run(
        self,
        command: str,
        *,
        timeout: Optional[float] = None,
        success_returncode=0,
        shell: Optional[Shell] = None,
    ):
        if shell is None:
            shell = Bash()

        missing_commands = [
            command
            for command in self.required_commands
            if shutil.which(command) is None
        ]

        if len(missing_commands) > 0:
            raise errors.JobRequiredCommandNotFound(
                missing=missing_commands, required=self.required_commands
            )

        logger.info(f"Executing: {command!r}...")

        if not self.dry_run:
            returncode = shell.execute(command, timeout=timeout)
            logger.info(f"Command {command!r} exited with {returncode} code.")

            if returncode != success_returncode:
                raise errors.JobCommandFailed(command, returncode)


_already_called: Set[Callable] = set()


class AlreadyCalledError(Exception): ...


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


class Pipeline:
    stages: List[str]
    jobs: List[Job]

    def __init__(self):
        self.stages = []
        self.jobs = []

    def __repr__(self):
        return f"Pipeline(stages={self.stages!r} jobs={self.jobs!r})"

    @require_call_once(error_message="Stages should be defined once")
    def define_stages(self, *stages: str):
        duplicated_stages: Set[str] = set()

        stage_counter = Counter()
        for stage in stages:
            stage_counter[stage] += 1
            if stage_counter[stage] > 1:
                duplicated_stages.add(stage)

        if len(duplicated_stages) > 0:
            raise errors.StagesAreAlreadyDefined(duplicated_stages, stages)

        self.stages = list(stages)

    def define_job(
        self, *, stage: str, require_commands: Optional[Sequence[str]] = None
    ) -> Callable[[JobHandler], JobHandler]:

        if require_commands is None:
            require_commands = []

        def internal(handler: JobHandler) -> JobHandler:
            nonlocal require_commands

            if stage not in self.stages:
                raise errors.StageIsNotDefined(
                    stage, defined_stages=self.stages
                )

            job = Job(
                stage=stage,
                handler=handler,
                required_commands=require_commands,
            )
            self.jobs.append(job)

            return handler

        return internal
