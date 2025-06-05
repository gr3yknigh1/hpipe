from __future__ import annotations
from typing import Any

from enum import StrEnum, IntEnum, auto

from htask import Context, Result


#
# VS utilities
#
DEFAULT_VC_BOOSTRAP_VARS = ["INCLUDE", "LIB", "LIBPATH", "PATH"]


def find_vcvars(c: Context) -> str | None:
    
    #
    # Detect vcvarsall for x64 build...
    #
    default_vc2022_bootstrap = r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
    default_vc2019_bootstrap = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Preview\VC\Auxiliary\Build\vcvarsall.bat"

    if c.exists(default_vc2022_bootstrap):
        return default_vc2022_bootstrap

    if c.exists(default_vc2019_bootstrap):
        return default_vc2019_bootstrap

    return None


def extract_env_from_vcvars(c: Context, arch="x64", vcvars: str | None = None, extract_vars: list[str] | None=None) -> dict[str, Any]:
    if vcvars is None:
        vcvars = find_vcvars(c)
        
        if vcvars is None:
            return {}

    if extract_vars is None:
        extract_vars = DEFAULT_VC_BOOSTRAP_VARS

    result = c.run(f"{c.quote(vcvars)} {arch} && set", capture_output=True)

    if result.output is None:
        return {}

    # NOTE(gr3yknigh1): Ha-ha, nasty, but it is on purpose! [2025/02/03]
    env = {
        item[0].upper() : item[1]
        for item in (
            l.split("=") for l in result.output.splitlines()
        ) if len(item) == 2 and item[0].upper() in extract_vars
    }

    return env

#
# MSVC command line helpers:
#
def format_defines(defines: dict[str, Any]) -> str:

    result = " ".join(
        [f"/D {k}={v}" for k, v in defines.items() ]
    )

    return result

def format_includes(includes: list[str]) -> str:
    result = " ".join(
        [f"/I {include}" for include in includes]
    )
    return result


class OutputKind(StrEnum):
    EXECUTABLE="executable"
    OBJECT_FILE="object_file"
    STATIC_LIBRARY="static_library"
    DYNAMIC_LIBRARY="dynamic_library"


class DebugInfoMode(StrEnum):
    NONE = "NONE"
    FASTLINK = "FASTLINK"
    FULL = "FULL"

class LanguageStandard(StrEnum):

    CXX_14 = "c++14"
    CXX_17 = "c++17"
    CXX_20 = "c++20"
    CXX_LATEST = "c++latest"

    C_11 = "c11"
    C_17 = "c17"
    C_LATEST = "clatest"


class RuntimeLibrary(IntEnum):
    STATIC = auto()
    STATIC_DEBUG = auto()
    DYNAMIC = auto()
    DYNAMIC_DEBUG = auto()


# TODO(gr3yknigh1): Expose more options to the user.
# See: https://learn.microsoft.com/en-us/cpp/build/reference/o1-o2-minimize-size-maximize-speed?view=msvc-170#remarks
# [2025/06/03]
    
class OptimizationLevel(IntEnum):
    DISABLED = auto()
    MINIMIZE_SIZE = auto()
    MAXIMIZE_SPEED = auto()
    

def compile(
    c: Context,
    sources: list[str],
    *,
    output: str,
    output_kind=OutputKind.EXECUTABLE,
    output_debug_info_path: str | None = None,
    libs: list[str] | None=None,
    defines: dict[str, Any] | None=None,
    includes: list[str] | None=None,
    compile_flags: list[str] | None=None,
    link_flags: list[str] | None=None,
    env: dict[str, Any] | None=None,
    only_preprocessor=False,
    only_compilation=False,
    produce_pdb=False,
    unicode_support=False,
    optimization_level: OptimizationLevel | None = None,
    language_standard: LanguageStandard | None = None,
    runtime_library: RuntimeLibrary | None = None,

    # TODO(gr3yknigh1): Refactor linker flags out from this function [2025/06/03]
    debug_info_mode: DebugInfoMode | None = None,
    is_dll=False, 
    **kw
):
    if env is None:
        env = {}

    if libs is None:
        libs = []

    if compile_flags is None:
        compile_flags = []

    if link_flags is None:
        link_flags = []

    if defines is None:
        defines = {}

    if includes is None:
        includes = []

    if unicode_support:
        defines.update(dict(
            UNICODE=1,
            _UNICODE=1,
        ))

    if only_compilation:
        compile_flags.append("/c")

    if only_preprocessor:
        compile_flags.append("/P")

    if produce_pdb:
        compile_flags.append("/Zi")

    if language_standard is not None:
        compile_flags.append(f"/std:{language_standard!s}")

    if runtime_library is not None:

        if runtime_library == RuntimeLibrary.STATIC:
            compile_flags.append("/MT")
        elif runtime_library == RuntimeLibrary.STATIC_DEBUG:
            compile_flags.append("/MTd")
        elif runtime_library == RuntimeLibrary.DYNAMIC:
            compile_flags.append("/MD")
        elif runtime_library == RuntimeLibrary.DYNAMIC_DEBUG:
            compile_flags.append("/MDd")
        else:
            raise NotImplementedError("...")

    if optimization_level is not None:

        if optimization_level == OptimizationLevel.DISABLED:
            compile_flags.append("/Od")
        elif optimization_level == OptimizationLevel.MINIMIZE_SIZE:
            compile_flags.append("/O1")
        elif optimization_level == OptimizationLevel.MAXIMIZE_SPEED:
            compile_flags.append("/O2")

    if is_dll:
        link_flags.append("/DLL")

    if debug_info_mode is not None:
        link_flags.append(f"/DEBUG:{debug_info_mode!s}")

    if output_debug_info_path is not None:
        compile_flags.append(f"/Fd:{output_debug_info_path}")

    compile_flags_formatted = " ".join(compile_flags)
    defines_formatted = format_defines(defines)
    includes_formatted = format_includes(includes)
    libs_formatted = " ".join(libs)
    sources_formatted = " ".join(sources)

    if len(link_flags) == 0:
        link_flags_formatted = ""
    else:
        link_flags_formatted = "/link {}".format(" ".join(link_flags))
    
    if output_kind == OutputKind.OBJECT_FILE:
        output_formatted = f"/Fo:{output}"
    else:
        output_formatted = f"/Fe:{output}"

    options = [
        compile_flags_formatted, defines_formatted, sources_formatted, output_formatted, includes_formatted, libs_formatted, link_flags_formatted
    ]

    options_formatted = " ".join(options)

    return c.run(
        f"cl.exe /nologo {options_formatted}",
        env=env, **kw
    )


def link(
    c: Context,
    object_files: list[str],
    *,
    output: str,
    output_kind=OutputKind.EXECUTABLE,
    output_debug_info_path: str | None = None,
    libraries: list[str] | None = None,
    env: dict[str, str] | None = None,
    kw: dict[str, Any] | None=None
) -> Result:

    if env is None:
        env = {}

    if kw is None:
        kw = {}

    if libraries is None:
        libraries = []

    object_files_formatted = " ".join(object_files)
    libraries_formatted  = " ".join(libraries)

    options = [object_files_formatted, libraries_formatted]

    if output_debug_info_path is not None and output_kind != OutputKind.STATIC_LIBRARY:
        options.append(f"/Fd:{output_debug_info_path}")

    options_formatted = " ".join(options)

    if output_kind == OutputKind.EXECUTABLE:
        result = c.run(f"link.exe /nologo {options_formatted}", env=env, **kw)
    elif output_kind == OutputKind.STATIC_LIBRARY:
        result = c.run(f"lib.exe /nologo /OUT:{output} {options_formatted}", env=env, **kw)
    elif output_kind == OutputKind.DYNAMIC_LIBRARY:
        result = c.run(f"cl.exe /nologo /LD /Fe:{output} {options_formatted}", env=env, **kw)
    else:
        raise NotImplementedError("...")

    return result


def show_includes(
    c: Context,
    source_file: str,
    *,
    includes: list[str] | None = None,
    macros: dict[str, str] | None = None,
    language_standard: LanguageStandard | None = None,
    env: dict[str, str] | None=None,
) -> list[str]:
    """Returns list of header-files on which given source file is dependent.

    :param includes: List of directories which should be added to include PATH.

    """

    if env is None:
        env = {}

    if includes is None:
        includes = []

    if macros is None:
        macros = {}

    options = []


    if language_standard is not None:
        options.append(f"/std:{language_standard!s}")

    if len(macros.keys()) > 0:
        options.append(format_defines(macros))

    if len(includes) > 0:
        options.append(format_includes(includes))

    options_formatted = " ".join(options)

    result = c.run(f"cl.exe /Zs {options_formatted} /showIncludes {source_file}", env=env, capture_output=True)
    assert result.output is not None

    prefix = "Note: including file:"

    include_files = []

    for line in result.output.split("\n"):
        if not line.startswith(prefix):

            if "error" in line or "warning" in line:
                raise Exception(f"Failed to retrive include files for source file! source={source_file} line={line!r}")

            continue
        line = line.replace(prefix, "", 1)
        line = line.strip()

        assert c.exists(line)
        include_files.append(line)

    return include_files


