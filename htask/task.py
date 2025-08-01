from __future__ import annotations
from typing import Callable, Any

from dataclasses import dataclass
from dataclasses import field
from contextlib import contextmanager
from copy import deepcopy
import subprocess
import shlex
import os
import sys

__all__ = ("Task", "define_task", "Result", "Config")


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
class Result:
    return_code: int
    output: str | None


@dataclass
class Context:
    root: str
    prefixes: list[str] = field(default_factory=list)
    config: Config = field(default_factory=Config)

    def quote(self, s: str) -> str:
        return f'"{s}"'

    def is_quoted(self, s: str) -> bool:
        return "\"" in (s[0], s[-1])

    def dequote(self, s: str) -> str:
        if self.is_quoted(s):
            return s[1:-1]
        return s

    def exists(self, p: str):
        return os.path.exists(p)

    def join(self, *parts: str) -> str:
        return os.path.join(*parts)

    def run(
        self,
        command: str,
        timeout: float | None = None,
        encoding="utf-8",
        capture_output=False,
        quiet=False,
        env: dict[str, Any] | None = None,
    ) -> Result:
        """Execute shell command.

        :param quiet: Overrides `self.confg.echo` for this call.
        """

        parts = [*self.prefixes, *shlex.split(command, posix=sys.platform != "win32")]
        parts[0] = self.dequote(parts[0])

        if env is None:
            env = {}

        env = {**os.environ, **env}

        if (self.config.dry_run or self.config.echo) and not quiet:
            print(f"> {' '.join(parts)}", flush=True)

        output: str | None = None
        return_code = 0

        if not self.config.dry_run:
            if capture_output:
                process = subprocess.Popen(
                    parts,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    cwd=self.root,
                )
                stdout, _ = process.communicate(timeout=timeout)
                output = (
                    stdout.decode(encoding) if stdout is not None else None
                )
            else:
                process = subprocess.Popen(
                    parts, 
                    shell=True,
                    env=env,
                    cwd=self.root,
                )
                process.wait(timeout=timeout)

            return_code = process.returncode

        return Result(
            return_code=return_code,
            output=output,
        )

    def cwd(self) -> str:
        return os.getcwd()

    @contextmanager
    def prefix(self, prefix: str):
        prefixes = deepcopy(self.prefixes)
        prefixes.append(prefix)

        try:
            yield Context(self.root, prefixes, self.config)
        finally:
            pass

    @contextmanager
    def cd(self, cd: str):
        try:
            yield Context(cd, self.prefixes, self.config)
        finally:
            pass

    # TODO(gr3yknigh1): Deprecate and remove this code. I do not known for sure is this good
    # idea to wrap common utilities. Original reason was to provide `echo` mode. Were you
    # can emulate what might happen during your task execution. Also I was what to provide
    # virtual FS for `echo` mode and `if-s` in this cases will be executed corretly
    # (when you trying to check existence of file).
    # [2025/06/10]
    def echo(self, msg: str) -> Result:
        if sys.platform == "win32":
            # NOTE(gr3yknigh1): Need no quotes in cmd.exe shell [2025/04/06]
            return self.run(f"echo {msg}")
        return self.run(f"echo {msg!r}")

    # NOTE(gr3yknigh1): Check note above `echo`. [2025/06/10]
    def mkdir(self, dir: str) -> Result:
        if self.config.dry_run:
            return self.run(f"mkdir {dir}")
        os.makedirs(dir, exist_ok=True)
        return Result(0, None)


orphan_tasks: list[Task] = []


def define_task(
    *,
    name: str | None = None,
    required_programs: list[str] | None = None,
):
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
