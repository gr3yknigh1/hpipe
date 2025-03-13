from __future__ import annotations
from typing import Callable
from typing import List
from typing import Set
from typing import Optional
from typing import Sequence
from typing import Dict

from collections import Counter
from collections import OrderedDict
from dataclasses import dataclass
from dataclasses import field
from logging import getLogger
from functools import partial
import subprocess
import shlex
import shutil

from hpipe import errors
from hpipe.requires import require_call_once

__all__ = ("Pipeline", "Job", "define_job")

Stage = str
JobProcedure = Callable[[...], None]

logger = getLogger("pipeline")


def echo(command: str):
    print(command)


def shell_execute(command: str, *, timeout: Optional[float] = None) -> int:
    process = subprocess.Popen(args=shlex.split(command))
    process.wait(timeout=timeout)
    return process.returncode


@dataclass
class Job:
    stage: Stage
    handler: JobProcedure = field(repr=False)
    required_programs: Sequence[str]

    dry_run: bool = field(default=False)

    def run(
        self,
        command: str,
        *,
        timeout: Optional[float] = None,
        success_returncode=0,
    ):
        missing_commands = [
            command
            for command in self.required_programs
            if shutil.which(command) is None
        ]

        if len(missing_commands) > 0:
            raise errors.JobRequiredCommandNotFound(
                missing=missing_commands, required=self.required_programs
            )

        if self.dry_run:
            echo(command)
            return

        returncode = shell_execute(command, timeout=timeout)

        if returncode != success_returncode:
            raise errors.JobCommandFailed(command, returncode)


class Pipeline:
    stages: List[Stage]
    jobs: List[Job]

    def __init__(self):
        self.stages = []
        self.jobs = []

    def __repr__(self):
        return f"Pipeline(stages={self.stages!r}, jobs={self.jobs!r})"

    @require_call_once(error_message="Stages should be defined once")
    def define_stages(self, *stages: Stage):
        duplicated_stages: Set[Stage] = set()

        stage_counter = Counter()
        for stage in stages:
            stage_counter[stage] += 1
            if stage_counter[stage] > 1:
                duplicated_stages.add(stage)

        if len(duplicated_stages) > 0:
            raise errors.StagesAreAlreadyDefined(duplicated_stages, stages)

        self.stages = list(stages)

    def define_job(
        self, *, stage: Stage, required_programs: Optional[Sequence[str]] = None
    ) -> Callable[[JobProcedure], JobProcedure]:

        if required_programs is None:
            required_programs = []

        def internal_job_procedure(job_procedure: JobProcedure) -> JobProcedure:

            job = Job(
                stage=stage,
                handler=job_procedure,
                required_programs=required_programs,
            )
            self.jobs.append(job)

            return job_procedure

        return internal_job_procedure


orphan_pipeline = Pipeline()
orphan_pipeline.define_stages("default")
define_job = partial(orphan_pipeline.define_job, stage="default")

def execute_job(job: Job, *, dry_run=False) -> None:
    _ = dry_run

    try:
        job.handler(job)
    except BaseException as e:
        logger.error("Exception during job execution", exc_info=e)
        raise errors.JobFailed()

def execute_pipeline(pipeline: Pipeline, *, dry_run=False) -> None:
    stages: Dict[str, List[Job]] = OrderedDict()

    for stage in pipeline.stages:
        stages[stage] = []

    for job in pipeline.jobs:

        # if job.stage is None:
        #     raise errors.StageCantBeNone(job, pipeline)

        if job.stage not in pipeline.stages:
            raise errors.StageIsNotDefined(job, pipeline.stages)

        stages[job.stage].append(job)

    for stage in stages.keys():
        jobs = stages[stage]

        if len(jobs) == 0:
            logger.warning(f"{stage!r} has no jobs!")
            continue

        failed_jobs: List[Job] = []

        for job in jobs:
            job.dry_run = dry_run

            try:
                execute_job(job, dry_run=dry_run)
            except errors.JobFailed:
                failed_jobs.append(job)

        if len(failed_jobs) > 0:
            break

