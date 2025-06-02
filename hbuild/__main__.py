from __future__ import annotations

from os.path import join
import argparse 
import sys
import os

from htask import Context

from hbuild import _targets
from hbuild import compile_project


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    argv = argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-C", "--directory", dest="working_dir", type=str, default=os.getcwd()
    )
    parser.add_argument(
        "-f", "--file", dest="build_file", type=str, default="hbuild.py"
    )
    parser.add_argument("-e", dest="echo", type=bool, default=True)
    parser.add_argument("-n", "--dry-run", dest="dry_run", default=False)

    args = parser.parse_args(argv)
    working_dir = getattr(args, "working_dir", None)
    assert working_dir

    working_dir = os.path.abspath(working_dir)

    build_file = getattr(args, "build_file", None)
    assert build_file

    dry_run = getattr(args, "dry_run", None)
    assert dry_run is not None

    echo = getattr(args, "echo", None)
    assert echo is not None


    c = Context(root=working_dir)

    compile_project(c, build_file=build_file, prefix=join(working_dir, "build"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
