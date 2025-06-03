from __future__ import annotations

from enum import StrEnum
from enum import IntEnum
from enum import auto
from dataclasses import dataclass, field
from copy import copy
from os import makedirs
from os.path import exists, isabs, join, splitext, basename
import sys
import importlib


from htask import Context
from htask.progs import msvc

__all__ = (
    "Target",
    "TargetKind",
    "add_target",
    "add_library",
    "add_executable",
    "compile_target",
    "compile_project",
    "Configuration",
    "configure",
    "BuildType",
    "Architecture",
    "Compiler",
)


_targets = []


class BuildType(StrEnum):
    DEBUG = "Debug"
    RELEASE = "Release"


class Architecture(StrEnum):
    X86_64 = "x86_64"


class Bitness(StrEnum):
    X32 = "x32"
    X64 = "x64"


_ARCH_TO_BITNESS = {
    Architecture.X86_64: Bitness.X64,
}
    

def arch_to_bitness(arch: Architecture) -> Bitness | None:
    return _ARCH_TO_BITNESS.get(arch, None)


class TargetKind(IntEnum):
    EXECUTABLE = auto()
    STATIC_LIBRARY = auto()
    DYNAMIC_LIBRARY = auto()

class TargetState(IntEnum):
    NOT_COMPILED = auto()
    ALREADY_COMPILED = auto()


class Compiler(StrEnum):
    MSVC = "msvc"

    @staticmethod
    def detect_compiler() -> Compiler:
        # TODO: Make more sofisticated algorithm... [2025/06/01]
        return Compiler.MSVC


_EXT_TO_LANGUAGE = {
    "C": (".c", ".h",),
}

class Language(StrEnum):
    C = "C"
    CXX = "CXX"

    @classmethod
    def guess_from_ext(cls, path: str) -> Language | None:

        _, file_ext = splitext(path)
        for lang, exts in _EXT_TO_LANGUAGE.items():
            if file_ext in exts:
                return cls(lang)
        return None


@dataclass
class SourceFile:
    path: str
    language: Language


@dataclass
class Target:
    name: str
    kind: TargetKind
    sources: list[InputFile] = field(default_factory=list)
    dependencies: list[Target] = field(default_factory=list)
    state: TargetState = field(default=TargetState.NOT_COMPILED)
    includes: list[str] = field(default_factory=list)
    defines: dict[str, str] = field(default_factory=dict)

    def get_artefact_ext(self, conf: Configuration) -> str:

        if conf.compiler == Compiler.MSVC:

            if self.kind == TargetKind.EXECUTABLE:
                return ".exe"

            if self.kind == TargetKind.STATIC_LIBRARY:
                return ".lib"

            if self.kind == TargetKind.DYNAMIC_LIBRARY:
                return ".dll"

        raise NotImplementedError("...")

    def get_artefact_path(self, conf: Configuration) -> str:
        ext = self.get_artefact_ext(conf)
        return join(conf.get_output_folder(), f"{self.name}{ext}")


def configure(
    c: Context,
    prefix: str,
    compiler=Compiler.detect_compiler(),
    build_type=BuildType.DEBUG,
    architecture=Architecture.X86_64
) -> Configuration:

    conf = Configuration(
        prefix=prefix,
        compiler=compiler,
        build_type=build_type,
        architecture=architecture,
    )

    output = conf.get_output_folder()
    makedirs(output, exist_ok=True)

    if conf.compiler == Compiler.MSVC:
        env = msvc.extract_env_from_vcvars(c, arch=arch_to_bitness(architecture))
        conf.environment.update(env)

    return conf


@dataclass
class Configuration:
    prefix: str
    compiler: Compiler
    build_type: BuildType
    architecture: Architecture

    environment: dict[str, str] = field(default_factory=dict)

    def get_output_folder(self):
        return join(
            self.prefix,
            arch_to_bitness(self.architecture), 
            self.build_type,
        )

def add_library(name: str, sources: list[str] | None = None, *, dynamic=False):
    if dynamic:
        return add_target(name, TargetKind.DYNAMIC_LIBRARY, sources)
    return add_target(name, TargetKind.STATIC_LIBRARY, sources)


def add_executable(name: str, sources: list[str] | None = None):
    return add_target(name, TargetKind.EXECUTABLE, sources)


def add_target(name: str, kind: TargetKind, sources: list[str] | None=None) -> Target:

    if sources is None:
        sources = []

    source_files = [
        SourceFile(
            path=source, language=Language.guess_from_ext(source)
        ) for source in sources
    ]

    target = Target(name=name, kind=kind, sources=source_files)

    for t in _targets:
        if t.name == target.name:
            raise Exception(f"Target with the same name was already defined: {t!r}.")

    _targets.append(target)

    return target

def compile_target(c: Context, *, conf: Configuration, target: Target):
    if target.state == TargetState.ALREADY_COMPILED:
        return

    for dependency in target.dependencies:
        compile_target(c, conf=conf, target=dependency)

    sources = []
    for source in target.sources:
        if not isabs(source.path):
            source.path = join(c.cwd(), source.path)
        sources.append(source)

    lost_sources = [source for source in sources if not exists(source.path)]
    if len(lost_sources) > 0:
        raise Exception(f"Non-existing sources was found! lost_sources={lost_sources!r}")

    target_output_prefix = join(conf.get_output_folder(), target.name)
    makedirs(target_output_prefix, exist_ok=True)

    if conf.compiler == Compiler.MSVC:

        # TODO(gr3yknigh1): Expose to the user the libraries which he want's to link [2025/06/02]
        libraries = ["kernel32.lib", "user32.lib", "gdi32.lib"]
        object_files: list[str] = []

        for source in sources:
            source_name, source_ext = splitext(basename(source.path))
            object_file = join(target_output_prefix, f"{source_name}.obj")

            if not isabs(source.path):
                source_path = join(c.cwd(), source.path)
            else:
                source_path = source.path

            if sys.platform == "win32":
                source_path = source_path.replace("/", "\\")
                target.includes = [include.replace("/", "\\") for include in target.includes]

            # TODO(gr3yknigh1): Expose this option via platform-specific API configurations [2025/06/03]
            runtime_library = (
                msvc.RuntimeLibrary.STATIC_DEBUG if conf.build_type == BuildType.DEBUG else msvc.RuntimeLibrary.STATIC
            )

            result = msvc.compile(
                c, [source_path],
                output=object_file,
                only_compilation=True,
                produce_pdb=conf.build_type == BuildType.DEBUG,
                includes=target.includes,
                defines=target.defines,
                output_kind=msvc.OutputKind.OBJECT_FILE,
                optimization_level=msvc.OptimizationLevel.DISABLED if conf.build_type == BuildType.DEBUG else msvc.OptimizationLevel.MAXIMIZE_SPEED,
                language_standard=msvc.LanguageStandard.C_LATEST if source.language == Language.C else msvc.LanguageStandard.CXX_14,
                debug_info_mode=msvc.DebugInfoMode.FULL if conf.build_type == BuildType.DEBUG else msvc.DebugInfoMode.NONE,
                runtime_library=runtime_library,
                env=conf.environment,
            )

            if result.return_code != 0:
                raise Exception(f"Failed to compile! return_code={result.return_code!r}")

            object_files.append(object_file)

        libraries.extend([dependency.get_artefact_path(conf) for dependency in target.dependencies])


        output = target.get_artefact_path(conf)
        output_filename, _ = splitext(output)

        compile_flags = []
        link_flags = []

        if conf.build_type == BuildType.DEBUG:
            # TODO(gr3yknigh1): Move to MSVC interface (msvc.py) [2025/06/02]

            compile_flags.extend([
                "/Zi",
            ])
            link_flags.extend([
                "/DEBUG:FULL",
            ])

        if target.kind == TargetKind.EXECUTABLE:
            result = msvc.compile(
                c, [],
                output=output,
                output_kind=msvc.OutputKind.EXECUTABLE,
                output_debug_info_path=f"{output_filename}.pdb",
                compile_flags=compile_flags,
                link_flags=link_flags,
                libs=[*object_files, *libraries],
                env=conf.environment,
            )
        elif target.kind == TargetKind.STATIC_LIBRARY:
            result = msvc.link(
                c, object_files,
                output=target.get_artefact_path(conf),
                output_kind=msvc.OutputKind.STATIC_LIBRARY,
                env=conf.environment,
            )
        elif target.kind == TargetKind.DYNAMIC_LIBRARY:
            result = msvc.link(
                c, object_files,
                output=target.get_artefact_path(conf),
                output_kind=msvc.OutputKind.DYNAMIC_LIBRARY,
                output_debug_info_path=f"{output_filename}.pdb",
                libraries=libraries,
                env=conf.environment,
            )
        else:
            raise NotImplementedError("...")

        if result.return_code != 0:
            raise Exception(f"Failed to compile! return_code={result.return_code!r}")
    else:
        raise NotImplementedError("Support only MSVC for now...")

    target.state = TargetState.ALREADY_COMPILED

    return result


def compile_project(
    c: Context,
    *,
    build_file: str,
    prefix: str,
    compiler=Compiler.detect_compiler(),
    build_type=BuildType.DEBUG,
    architecture=Architecture.X86_64,
) -> Result:

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

    # TODO(gr3yknigh1): Expose more configuration stuff in command-line [2025/06/01]
    conf = configure(
        c,
        compiler=compiler,
        build_type=build_type,
        architecture=architecture,
        prefix=prefix,
    )

    for target in _targets:
        compile_target(c, conf=conf, target=target)
