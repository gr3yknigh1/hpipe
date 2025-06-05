from __future__ import annotations

from enum import StrEnum, IntEnum, auto
from dataclasses import dataclass, field
from os import makedirs
from os.path import exists, isabs, join, splitext, basename, dirname
from copy import copy
import importlib.util
import sys
import inspect


from htask import Context
from htask.progs import msvc, cmake

__all__ = (
    "Target",
    "TargetKind",
    "add_package",
    "add_target",
    "add_executable",
    "add_library",
    "add_external_library",
    "compile_target",
    "compile_package",
    "Configuration",
    "configure",
    "BuildType",
    "Architecture",
    "Compiler",
    "BuildTool",
    "Access",
    "target_includes",
    "target_macros",
    "target_links",
)

HBUILD_MAGIC_PACKAGE_LIST_ATTR_NAME = "__hbuild_magic_package_list__"



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
    "C": (
        ".c",
        ".h",
    ),
    "CXX": (
        ".cpp",
        ".hpp",
        ".cxx",
        ".hxx",
        ".cc",
        ".hh",
    )
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
class TargetProperties:
    includes: list[str] = field(default_factory=list)
    macros: dict[str, str] = field(default_factory=dict)

    # ?
    links: list[Target] = field(default_factory=list)

    def merge(self, other: TargetProperties) -> TargetProperties:
        new = TargetProperties()

        new.includes.extend(self.includes)
        new.includes.extend(other.includes)

        new.macros.update(**self.macros)
        new.macros.update(**other.macros)

        return new


class Access(IntEnum):
    PRIVATE = auto()
    PUBLIC = auto()


@dataclass
class Target:
    name: str
    kind: TargetKind
    state: TargetState = field(default=TargetState.NOT_COMPILED)

    sources: list[SourceFile] = field(default_factory=list)

    properties: dict[Access, TargetProperties] = field(default_factory=dict)

    external_build: ExternalBuildProps | None = field(default=None)

    def __post_init__(self):
        for access in Access:
            self.properties[access] = TargetProperties()


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

        if self.external_build is not None:
            # TODO(gr3yknigh1): Find better way of handling properties of external dependencies. [2025/06/03]

            if self.external_build.tool == BuildTool.CMAKE:

                # TODO(gr3yknigh1): Check for multi-config generators. See: https://cmake.org/cmake/help/latest/prop_gbl/GENERATOR_IS_MULTI_CONFIG.html o
                # [2025/06/03]
                return join(conf.get_output_folder(), ".external.cmake", self.name, self.name, conf.build_type, f"{self.name}{ext}")

            if self.external_build.tool == BuildTool.HBUILD:
                return join(conf.get_output_folder(), f"{self.name}{ext}" )

            breakpoint()
            raise NotImplementedError("...")

        return join(conf.get_output_folder(), f"{self.name}{ext}")


def configure(
    c: Context,
    prefix: str,
    build_file: str,
    compiler=Compiler.detect_compiler(),
    build_type=BuildType.DEBUG,
    architecture=Architecture.X86_64,
) -> Configuration:
    conf = Configuration(
        prefix=prefix,
        build_file=build_file,
        compiler=compiler,
        build_type=build_type,
        architecture=architecture,
    )

    output = conf.get_output_folder()
    makedirs(output, exist_ok=True)

    if conf.compiler == Compiler.MSVC:
        env = msvc.extract_env_from_vcvars(
            c, arch=arch_to_bitness(architecture)
        )
        conf.environment.update(env)

    return conf


@dataclass
class Configuration:
    prefix: str
    build_file: str
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

    def get_project_folder(self):
        return dirname(self.build_file)

@dataclass
class Package:
    name: str
    targets: Target


def add_package(name: str, *, targets: list[Target]) -> Package:
    frame = inspect.currentframe()
    
    try:
        current = frame
        while HBUILD_MAGIC_PACKAGE_LIST_ATTR_NAME not in current.f_globals.keys():
            current = current.f_back
        else:

            new = Package(name, targets)

            packages: list[Package] | None = current.f_globals.get(HBUILD_MAGIC_PACKAGE_LIST_ATTR_NAME, None)
            assert packages is not None

            for package in packages:
                if package.name == new:
                    raise Exception(f"Found package with the same name as new! new={new!r} old={package!r}")

            packages.append(new)
            return new

    finally:
        del frame

    raise Exception("Failed to find magic list of packages! You might be called not from build file?")
    

def add_library(name: str, sources: list[str] | None = None, *, dynamic=False) -> Target:
    if dynamic:
        return add_target(name, TargetKind.DYNAMIC_LIBRARY, sources)
    return add_target(name, TargetKind.STATIC_LIBRARY, sources)


class BuildTool(IntEnum):
    HBUILD = auto()
    CMAKE = auto()


@dataclass
class ExternalBuildProps:
    tool: BuildTool
    location: str
    build_file: str = field(default="build.py")


def add_external_library(name: str, *, location: str, tool=BuildTool.HBUILD, dynamic=False) -> Target:
    return add_target(
        name,
        kind=(
            TargetKind.DYNAMIC_LIBRARY
            if dynamic
            else TargetKind.STATIC_LIBRARY
        ),
        external_build=ExternalBuildProps(
            tool=tool,
            location=location,
        )
    )


def add_executable(name: str, sources: list[str] | None = None):
    return add_target(name, TargetKind.EXECUTABLE, sources)


def target_includes(target: Target, access=Access.PRIVATE, *, includes: list[str]) -> None:
    assert len(includes) > 0
    target.properties[access].includes.extend(includes)


def target_macros(target: Target, access=Access.PRIVATE, *, macros: dict[str, str]) -> None:
    assert len(macros) > 0
    target.properties[access].macros.update(**macros)


def target_links(target, access=Access.PRIVATE, *, links: list[Target]) -> None:
    assert len(links) > 0
    target.properties[access].links.extend(links)


def add_target(
    name: str,
    kind: TargetKind,
    sources: list[str] | None = None,
    external_build: ExternalBuildProps | None = None,
) -> Target:

    if sources is None:
        sources = []

    source_files = []

    for source in sources:
        language = Language.guess_from_ext(source)

        if language is None:
            raise Exception("Failed to guess language via extension.")  # XXX

        source_files.append(SourceFile(path=source, language=language))

    target = Target(name=name, kind=kind, sources=source_files, external_build=external_build)

    return target


def compile_target(c: Context, *, conf: Configuration, target: Target) -> TargetProperies:
    """ Compiles the target and it's dependencies.

    :returns: All public properties, propagated from the bottom of dependency graph.
    """

    public_props = TargetProperties(
        macros=target.properties[Access.PUBLIC].macros,
        includes=target.properties[Access.PUBLIC].includes,
    )

    # TODO(gr3yknigh1): This breaks the external builds... Public props not filled with parsed information about packages. [2025/06/05]
    # if target.state == TargetState.ALREADY_COMPILED:
    #     return public_props

    if target.external_build is not None:

        external_build = target.external_build

        if external_build.tool == BuildTool.HBUILD:

            result_props = compile_package(
                c,
                build_file=join(external_build.location, external_build.build_file),
                prefix=conf.prefix,

                # TODO(gr3yknigh1): Maybe it's better to pass Configuration? [2025/06/04]
                compiler=conf.compiler,
                build_type=conf.build_type,
                architecture=conf.architecture,
            )

            for index, include in enumerate(copy(result_props.includes)):
                if not isabs(include):
                    result_props.includes[index] = join(target.external_build.location, include)

            public_props = public_props.merge(result_props)
            
        elif external_build.tool == BuildTool.CMAKE:
            # TODO(gr3yknigh1): Find better way of handling properties of external dependencies. [2025/06/03]

            target_output_folder = join(conf.get_output_folder(), ".external.cmake", target.name)
            makedirs(target_output_folder, exist_ok=True)

            cmake.configure(
                c,
                source_folder=target.external_build.location,
                build_folder=target_output_folder,
                variables=dict(
                    CMAKE_BUILD_TYPE=conf.build_type,
                )
            )

            cmake.build(
                c,
                configuration_name=conf.build_type,
                source_folder=target.external_build.location,
                build_folder=target_output_folder,
            )
        else:
            raise NotImplementedError(f"Unhandled external tool! {target.external_build!r}")

        target.state = TargetState.ALREADY_COMPILED
        return public_props

    # This is used to compile current target.
    libraries = []
    includes = []
    macros = {}

    # Include all props from this target
    for _, properties in target.properties.items():
        includes.extend(properties.includes)
        macros.update(**properties.macros)


    # Compile dependencies, gather and include all public props from them.
    for _, props in target.properties.items():
        for link_target in props.links:

            # Propagated properties from the bottom of dependency graph. 
            link_public_props: TargetProperties = compile_target(c, conf=conf, target=link_target)

            includes.extend(link_public_props.includes)
            macros.update(**link_public_props.macros)

            libraries.append(link_target.get_artefact_path(conf))
            public_props = public_props.merge(link_public_props)

    sources = []
    for source in target.sources:
        if not isabs(source.path):
            source.path = join(conf.get_project_folder(), source.path)
        sources.append(source)

    lost_sources = [source for source in sources if not exists(source.path)]
    if len(lost_sources) > 0:
        raise Exception(
            f"Non-existing sources was found! lost_sources={lost_sources!r}"
        )

    target_output_prefix = join(conf.get_output_folder(), target.name)
    makedirs(target_output_prefix, exist_ok=True)
 
    for index, include in enumerate(copy(includes)):
        if not isabs(include):
            includes[index] = join(conf.get_project_folder(), include)

    if sys.platform == "win32":
        includes = [include.replace("/", "\\") for include in includes]


    if conf.compiler == Compiler.MSVC:
        # TODO(gr3yknigh1): Expose to the user the libraries which he want's to link [2025/06/02]
        libraries.extend(["kernel32.lib", "user32.lib", "gdi32.lib"])
        object_files: list[str] = []

        # TODO(gr3yknigh1): Expose this option via platform-specific API configurations [2025/06/03]
        runtime_library = (
            msvc.RuntimeLibrary.STATIC_DEBUG
            if conf.build_type == BuildType.DEBUG
            else msvc.RuntimeLibrary.STATIC
        )


        debug_info_mode = (
            msvc.DebugInfoMode.FULL
            if conf.build_type == BuildType.DEBUG
            else msvc.DebugInfoMode.NONE
        )

        optimization_level = (
            msvc.OptimizationLevel.DISABLED
            if conf.build_type == BuildType.DEBUG
            else msvc.OptimizationLevel.MAXIMIZE_SPEED
        )

        for source in sources:
            source_name, source_ext = splitext(basename(source.path))
            object_file = join(target_output_prefix, f"{source_name}.obj")

            # NOTE(gr3yknigh1): Currently supporting C and C++ ;C [2025/06/03]
            language_standard = (
                msvc.LanguageStandard.C_LATEST
                if source.language == Language.C
                else msvc.LanguageStandard.CXX_LATEST
            )

            if not isabs(source.path):
                source_path = join(c.cwd(), source.path)
            else:
                source_path = source.path

            if sys.platform == "win32":
                source_path = source_path.replace("/", "\\")

            result = msvc.compile(
                c,
                [source_path],
                output=object_file,
                only_compilation=True,
                produce_pdb=conf.build_type == BuildType.DEBUG,
                includes=includes,
                defines=macros,
                output_kind=msvc.OutputKind.OBJECT_FILE,
                optimization_level=optimization_level,
                language_standard=language_standard,
                debug_info_mode=debug_info_mode,
                runtime_library=runtime_library,
                env=conf.environment,
            )

            if result.return_code != 0:
                raise Exception(
                    f"Failed to compile! return_code={result.return_code!r}"
                )

            object_files.append(object_file)

        output = target.get_artefact_path(conf)
        output_filename, _ = splitext(output)

        compile_flags = []
        link_flags = []

        if conf.build_type == BuildType.DEBUG:
            # TODO(gr3yknigh1): Move to MSVC interface (msvc.py) [2025/06/02]

            compile_flags.extend(
                [
                    "/Zi",
                ]
            )
            link_flags.extend(
                [
                    "/DEBUG:FULL",
                ]
            )

        if target.kind == TargetKind.EXECUTABLE:
            result = msvc.compile(
                c,
                [],
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
                c,
                object_files,
                output=target.get_artefact_path(conf),
                output_kind=msvc.OutputKind.STATIC_LIBRARY,
                env=conf.environment,
            )
        elif target.kind == TargetKind.DYNAMIC_LIBRARY:
            result = msvc.compile(
                c,
                object_files,
                output=target.get_artefact_path(conf),
                output_kind=msvc.OutputKind.DYNAMIC_LIBRARY,
                output_debug_info_path=f"{output_filename}.pdb",
                debug_info_mode=debug_info_mode,
                produce_pdb=conf.build_type == BuildType.DEBUG,
                libs=libraries,
                env=conf.environment,
                is_dll=True,
            )
        else:
            raise Exception(f"Unhandled kind of targets! kind={target.kind!r}.")

        if result.return_code != 0:
            raise Exception(
                f"Failed to compile! return_code={result.return_code!r}"
            )
    else:
        raise NotImplementedError("Sorry. We are supporting only MSVC for now...")

    target.state = TargetState.ALREADY_COMPILED

    return public_props


# TODO: Rename back to projects...
def compile_package(
    c: Context,
    *,
    build_file: str,
    prefix: str,
    compiler=Compiler.detect_compiler(),
    build_type=BuildType.DEBUG,
    architecture=Architecture.X86_64,
) -> TargetProperties:
    filename = basename(build_file)

    module_spec = importlib.util.spec_from_file_location(
        filename, build_file
    )

    if module_spec is None:
        raise NotImplementedError()

    module = importlib.util.module_from_spec(module_spec)
    setattr(module, HBUILD_MAGIC_PACKAGE_LIST_ATTR_NAME, [])

    if module_spec.loader is None:
        raise NotImplementedError()

    module_spec.loader.exec_module(module)

    packages: list[Package] | None = getattr(module, HBUILD_MAGIC_PACKAGE_LIST_ATTR_NAME, None)
    assert packages is not None


    if len(packages) <= 0:
        raise Exception("No packages was found! Use `add_package` in order to wrap targets in compilable project.")
    properties = TargetProperties()
    # TODO(gr3yknigh1): Expose more configuration stuff in command-line [2025/06/01]
    conf = configure(
        c,
        build_file=build_file,
        compiler=compiler,
        build_type=build_type,
        architecture=architecture,
        prefix=prefix,
    )

    for package in packages:
        for target in package.targets:
            properties = properties.merge(compile_target(c, conf=conf, target=target))

    return properties
