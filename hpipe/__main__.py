from typing import Any
from typing import Optional

from argparse import ArgumentParser
from dataclasses import dataclass
import importlib
import importlib.util
import sys
import os
import os.path
import logging

from hpipe.pipeline import Pipeline
from hpipe.internal import execute_pipeline

PIPELINE_ROOT_MODULE_NAME = "__hpipe_root_pipeline__"


@dataclass
class _PathNotExists(Exception):
    path: str

    def __post_init__(self):
        super().__init__(
            f"Path doesn't exists: {self.path!r}",
        )


@dataclass
class _PipelineInstanceNotFound(Exception):
    instance_var: str
    pipeline_path: str

    def __post_init__(self):
        super().__init__(
            f"Failed to find pipeline instance in module[{self.pipeline_path!r}]: {self.instance_var!r}",
        )


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("cli")


def _handler_help(parser: ArgumentParser, args: Any):
    _ = args

    parser.print_help()

def _handler_run(parser: ArgumentParser, args: Any):
    _ = parser

    root_dir: str = os.path.abspath(args.root_dir)
    pipeline_file: str = args.pipeline_file
    pipeline_var: str = args.pipeline_var
    dry_run: bool = args.dry_run

    if not os.path.exists(root_dir):
        raise _PathNotExists(root_dir)

    pipeline_file_path = os.path.join(root_dir, pipeline_file)

    if not os.path.exists(pipeline_file_path):
        raise _PathNotExists(pipeline_file_path)

    pipeline_module_spec = importlib.util.spec_from_file_location(
        PIPELINE_ROOT_MODULE_NAME, pipeline_file_path
    )

    if pipeline_module_spec is None:
        raise NotImplementedError()

    pipeline_module = importlib.util.module_from_spec(pipeline_module_spec)

    if pipeline_module_spec.loader is None:
        raise NotImplementedError()

    sys.modules[PIPELINE_ROOT_MODULE_NAME] = pipeline_module
    pipeline_module_spec.loader.exec_module(pipeline_module)

    logger.debug(f"PIPELINE_MODULE: {pipeline_module!r}")
    pipeline_instance: Optional[Pipeline] = getattr(
        pipeline_module, pipeline_var, None
    )

    if pipeline_instance is None:
        raise _PipelineInstanceNotFound(pipeline_var, pipeline_file_path)

    logger.debug(f"PIPELINE_INSTANCE: {pipeline_instance!r}")

    execute_pipeline(pipeline_instance, dry_run=dry_run)


def main() -> int:
    parser = ArgumentParser()
    parser.set_defaults(handler=_handler_help)

    subparsers = parser.add_subparsers()

    help_parser = subparsers.add_parser("help")
    help_parser.set_defaults(handler=_handler_help)

    run_parser = subparsers.add_parser("run")
    run_parser.set_defaults(handler=_handler_run)
    run_parser.add_argument("root_dir", default=os.curdir, nargs="?")
    run_parser.add_argument(
        "-p", "--pipeline-file", default="pipeline.py", dest="pipeline_file"
    )
    run_parser.add_argument(
        "-v", "--pipeline-var", default="pipeline", dest="pipeline_var"
    )
    run_parser.add_argument(
        "-n", "--dry-run", default=False, dest="dry_run", action="store_true"
    )

    args = parser.parse_args()
    args.handler(parser, args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
