from __future__ import annotations

from os.path import join
import argparse 
import sys
import os
import importlib

from htask import Context

from hbuild import _targets
from hbuild import compile_target, configure


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

    if working_dir:
        os.chdir(working_dir)

    module_spec_name = "__hbuild_build_file__"
    
    module_spec = importlib.util.spec_from_file_location(
        module_spec_name, build_file
    )

    if module_spec is None:
        raise NotImplementedError()

    module = importlib.util.module_from_spec(module_spec)

    if module_spec.loader is None:
        raise NotImplementedError()

    sys.modules[module_spec_name] = module
    module_spec.loader.exec_module(module)

    c = Context(root=working_dir)

    # TODO(gr3yknigh1): Expose more configuration stuff in command-line [2025/06/01]
    conf = configure(c, prefix=join(working_dir, "build")) 

    #with c.cd(conf.get_output_folder()) as c:
    for target in _targets:
        compile_target(c, conf=conf, target=target)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
