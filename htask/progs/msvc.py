from __future__ import annotations

from typing import Any

from enum import StrEnum

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

def compile(
    c: Context,
    sources: list[str],
    *,
    output: str,
    output_kind=OutputKind.EXECUTABLE,
    libs: list[str] | None=None,
    defines: dict[str, Any] | None=None,
    includes: list[str] | None=None,
    compile_flags: list[str] | None=None,
    link_flags: list[str] | None=None,
    env: dict[str, Any] | None=None,
    only_preprocessor=False,
    unicode_support=False,
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

    if only_preprocessor:
        compile_flags.append("/P")

    if is_dll:
        link_flags.append("/DLL")

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
    elif output_kind == OutputKind.EXECUTABLE:
        output_formatted = f"/Fe:{output}"
    else:
        raise NotImplementedError("")

    options = " ".join([
        compile_flags_formatted, defines_formatted, sources_formatted, output_formatted, includes_formatted, libs_formatted, link_flags_formatted
    ])

    return c.run(
        f"cl.exe /nologo {options}",
        env=env, **kw
    )


def link(
    c: Context,
    object_files: list[str],
    *,
    output: str,
    output_kind=OutputKind.EXECUTABLE,
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

    options = " ".join([object_files_formatted, libraries_formatted])

    if output_kind == OutputKind.EXECUTABLE:
        result = c.run(f"link.exe /nologo {options}", env=env, **kw)
    elif output_kind == OutputKind.STATIC_LIBRARY:
        result = c.run(f"lib.exe /nologo /OUT:{output} {options}", env=env, **kw)
    elif output_kind == OutputKind.DYNAMIC_LIBRARY:
        result = c.run(f"link.exe /nologo /DLL /OUT:{output} {options}", env=env, **kw)
    else:
        raise NotImplemented("...")
    return result
