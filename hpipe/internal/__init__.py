from typing import Dict
from typing import List

from logging import getLogger
from collections import OrderedDict

from hpipe.pipeline import Pipeline
from hpipe.pipeline import Job
from hpipe import errors

__all__ = ("execute_pipeline",)

logger = getLogger("internal")


def execute_job(job: Job) -> None:
    try:
        job.handler(job)
    except BaseException as e:
        logger.error("Exception during job execution", exc_info=e)
        raise errors.JobFailed()


def execute_pipeline(pipeline: Pipeline) -> None:
    stages: Dict[str, List[Job]] = OrderedDict()

    for stage in pipeline.stages:
        stages[stage] = []

    for job in pipeline.jobs:
        if job.stage not in pipeline.stages:
            raise errors.StageIsNotDefined(job.stage, pipeline.stages)
        stages[job.stage].append(job)

    for stage in stages.keys():
        jobs = stages[stage]

        logger.debug(f"JOBS: {jobs!r}")

        if len(jobs) == 0:
            logger.warning(f"{stage!r} stage has no jobs. Skipping...")
            continue

        logger.info(f"Starting stage: {stage!r}")

        failed_jobs: List[Job] = []

        for job in jobs:
            try:
                execute_job(job)
            except errors.JobFailed:
                failed_jobs.append(job)

        if len(failed_jobs) > 0:
            logger.info("Exiting pipeline execution...")
            break

