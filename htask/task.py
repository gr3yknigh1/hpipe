from __future__ import annotations
from typing import Callable

from dataclasses import dataclass
from dataclasses import field
import subprocess
import shlex


__all__ = ("Task", "define_task")


@dataclass
class Task:
    procedure: Callable
    name: str
    required_programs: list[str] = field(default_factory=list)

@dataclass
class Config:
    dry_run: bool = field(default=False)
    echo: bool = field(default=True)

@dataclass
class Context:
    config: Config = field(default_factory=Config)

    def run(self, command: str, timeout: float | None = None) -> int:

        if self.config.dry_run or self.config.echo:
            print(f"> {command}")

        if not self.config.dry_run:
            process = subprocess.Popen(shlex.split(command), shell=True)
            # TODO(gr3yknigh1): Replace shlex.split with custom splitter, because shlex only suitable for POSIX shells [2025/03/16] 
            
            process.wait(timeout=timeout)
            return_code = process.returncode
        else:
            return_code = 0

        return return_code

orphan_tasks: list[Task] = []

def define_task(*, name: str | None = None, required_programs: list[str] | None =None, ):
    def internal_task_procedure(task_procedure: Callable) -> Callable:
        nonlocal required_programs, name

        if name is None:
            name = task_procedure.__name__

        if required_programs is None:
            required_programs = []

        task = Task(
            procedure=task_procedure,
            name=name,
            required_programs=required_programs,
        )
        
        orphan_tasks.append(task)
        return task_procedure

    return internal_task_procedure

