from __future__ import annotations
from typing import Any
from typing import TypeVar
from typing import Callable

from functools import partial
import os
import sys
import inspect
import importlib.util

from htask import Task, Context, Config
from htask.task import orphan_tasks
from htask.parser import ArgumentDescription, ArgumentStoreType


SWITCH_START = "-"


Ty = TypeVar("Ty")


class ArgumentParser:
    arguments: list[ArgumentDescription[Any]]

    parse_arguments: list[str]
    parse_index: int
    parse_current: str

    def __init__(self):
        self.arguments = []

        self.parse_arguments = []
        self.parse_index = -1
        self.parse_current = ""

    def parse_advance(self) -> str:
        if self.parse_index < len(self.parse_arguments):
            self.parse_index += 1

        if self.parse_index < len(self.parse_arguments):
            self.parse_current = self.parse_arguments[self.parse_index]
        return self.parse_current

    def peek_argument(self, offset: int) -> str:
        if self.parse_index + offset < len(self.parse_arguments):
            return self.parse_arguments[self.parse_index + offset]
        return self.parse_arguments[len(self.parse_arguments) - 1]

    def should_stop(self) -> bool:
        return self.parse_index >= len(self.parse_arguments)

    def add_argument(
        self,
        *switches: str,
        dest: str,
        type: Callable[[str], Ty] = str,
        format=ArgumentStoreType.STORE_VALUE,
        default: Ty | None = None,
    ) -> ArgumentDescription[Ty]:
        new_argument: ArgumentDescription[Ty] = ArgumentDescription(
            dest=dest,
            switches=list(switches),
            type=type,
            format=format,
            default=default,
        )

        for argument in self.arguments:
            if dest != argument.dest:
                continue
            raise Exception(
                f"Already have option with same 'dest'! new={new_argument!r} old={argument!r}"
            )  # @cleanup

        self.arguments.append(new_argument)
        return new_argument

    def parse_args(self, arguments: list[str]) -> dict[str, Any]:
        self.parse_arguments = arguments
        return self.parse_switches(self.arguments)

    def parse_switches(
        self, arguments: list[ArgumentDescription] | None = None
    ) -> dict[str, Any | None]:
        # NOTE(gr3yknigh1): Hack! [2025/03/16]
        if arguments is None:
            arguments = self.arguments

        swicthes: dict[str, Any | None] = {
            argument.dest: argument.default for argument in arguments
        }

        while self.peek_argument(1).startswith(SWITCH_START) and not self.should_stop():
            self.parse_advance()

            for argument in arguments:
                if self.parse_current not in argument.switches:
                    continue
                if argument.format == ArgumentStoreType.STORE_VALUE:
                    swicthes[argument.dest] = argument.type(
                        self.parse_advance()
                    )
                elif argument.format == ArgumentStoreType.STORE_TRUE:
                    swicthes[argument.dest] = True
                elif argument.format == ArgumentStoreType.STORE_FALSE:
                    swicthes[argument.dest] = False
                break
            else:
                raise Exception(
                    f"Unrecognized argument: {self.parse_current!r}. Argument={arguments!r}"
                )

        self.parse_advance()
        return swicthes

    def parse_task_args(
        self, descriptions: dict[str, list[ArgumentDescription]]
    ) -> tuple[list[str], dict[str, dict[str, Any]], list[str]]:
        requested_tasks: list[str] = []
        arguments: dict[str, dict[str, Any]] = {}
        unknown_tasks: list[str] = []

        while not self.should_stop():
            task_name = self.parse_current

            if task_name not in descriptions.keys():
                unknown_tasks.append(task_name)
                # NOTE(gr3yknigh1): Skipping options of unknown task [2025/03/16]
                while self.peek_argument(1).startswith(SWITCH_START):
                    _ = self.parse_advance(), self.parse_advance()
            else:
                requested_tasks.append(task_name)
                arguments[task_name] = self.parse_switches(
                    descriptions[task_name]
                )

            self.parse_advance()

        return requested_tasks, arguments, unknown_tasks


def load_tasks(
    task_file: str, module_spec_name="__htask_root_tasks__"
) -> list[Task]:
    if not os.path.exists(task_file):
        raise Exception(f"Task file not found! {task_file!r}")

    module_spec = importlib.util.spec_from_file_location(
        module_spec_name, task_file
    )

    if module_spec is None:
        raise NotImplementedError()

    module = importlib.util.module_from_spec(module_spec)

    if module_spec.loader is None:
        raise NotImplementedError()

    sys.modules[module_spec_name] = module
    module_spec.loader.exec_module(module)

    tasks: list[Task] = orphan_tasks
    return tasks


def run_tasks(
    context: Context,
    requested_tasks: list[str],
    defined_tasks: list[Task],
    tasks_args: dict[str, dict[str, Any]],
):
    for requested_task in requested_tasks:
        for task in defined_tasks:
            if requested_task != task.name:
                continue

            procedure = partial(
                task.procedure, context, **tasks_args[task.name]
            )
            procedure()


def generate_argument_descriptions_for_tasks(
    tasks: list[Task],
) -> dict[str, list[ArgumentDescription]]:
    result: dict[str, list[ArgumentDescription]] = {}

    for task in tasks:
        # XXX
    
        if task.name not in result.keys():
            result[task.name] = []

        sig = inspect.signature(task.procedure)

        for p_index, (p_name, p_obj) in enumerate(sig.parameters.items()):
            # TODO(gr3yknigh1): Handle string type annotation [2025/03/16]
            if (
                p_index == 0
                and p_obj.annotation != p_obj.empty
                and p_obj.annotation is not Context
            ):
                raise Exception("First argument should be Context object!")

            if p_index == 0:
                continue

            p_type: type | None = (
                p_obj.annotation
                if p_obj.annotation != p_obj.empty
                else (
                    type(p_obj.default)
                    if p_obj.default != p_obj.empty
                    else None
                )
            )

            result[task.name].append(
                ArgumentDescription(
                    dest=p_name.replace("_", "-"),
                    switches=generate_switches(p_name),
                    type=lambda v: p_type(v) if p_type is not None else str,
                    format=(
                        ArgumentStoreType.STORE_VALUE
                        if p_type is not bool
                        else ArgumentStoreType.STORE_TRUE
                    ),
                    default=(
                        p_obj.default if p_obj.default != p_obj.empty else None
                    ),
                )
            )

    return result


def generate_switches(name: str) -> list[str]:
    result = []
    result.append("{}{}".format(SWITCH_START, name[0]))
    result.append(
        "{}{}{}".format(SWITCH_START, SWITCH_START, name.replace("_", "-"))
    )
    return result


def main(argv: list[str] | None = None) -> int:
    argv = argv[1:] if argv is not None else []

    parser = ArgumentParser()
    parser.add_argument(
        "-C", "--directory", dest="working_dir", type=str, default=os.getcwd()
    )
    parser.add_argument(
        "-f", "--file", dest="task_file", type=str, default="tasks.py"
    )
    parser.add_argument("-e", dest="echo", type=bool, default=True)
    parser.add_argument("-n", "--dry-run", dest="dry_run", default=False)

    args = parser.parse_args(argv)
    working_dir = args.get("working_dir")
    assert working_dir

    task_file = args.get("task_file")
    assert task_file

    dry_run = args.get("dry_run")
    assert dry_run is not None

    echo = args.get("echo")
    assert echo is not None

    if working_dir:
        os.chdir(working_dir)

    defined_tasks = load_tasks(os.path.join(working_dir, task_file))
    descriptions = generate_argument_descriptions_for_tasks(defined_tasks)

    requested_tasks, tasks_args, unknown_tasks = parser.parse_task_args(
        descriptions
    )

    if len(unknown_tasks) > 0:
        raise Exception(f"Found unknown tasks! {unknown_tasks!r}")

    if len(requested_tasks) == 0:
        print("I: Nothing to run...")
        return 0

    context = Context(
        root=working_dir,
        config=Config(
            dry_run=dry_run,
            echo=echo,
        )
    )

    run_tasks(context, requested_tasks, defined_tasks, tasks_args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
    raise SystemExit(main(["htask", "build", "--reconfigure"]))
    raise SystemExit(main(["htask", "-C", "examples/03_basic_project"]))
    raise SystemExit(
        main(
            [
                "htask",
                "-C",
                "examples/03_basic_project",
                "build",
                "-c",
                "Release",
            ]
        )
    )
