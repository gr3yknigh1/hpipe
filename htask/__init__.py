from __future__ import annotations
from typing import Any

from htask.task import Task
from htask.task import Context
from htask.task import Config
from htask.task import Result
from htask.task import define_task

__all__ = ("Task", "define_task", "Context", "Config", "load_env", "save_env", "is_file_busy")

def load_env(file: str) -> dict[str, str]:
    with open(file, mode="r") as f:
        s = f.read()

        env = {
            item[0]: item[1]
            for item in (l.split("=") for l in s.splitlines())
            if len(item) == 2
        }
    return env

def save_env(file: str, env: dict[str, Any]) -> None:
    with open(file, mode="w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")

def is_file_busy(file: str, mode: str="w") -> bool:
    try:
        with open(file, mode=mode):
            return False
    except IOError:
        return True
