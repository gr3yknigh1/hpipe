from hpipe import Pipeline, Context

pipeline = Pipeline()
pipeline.define_stages("echo")

@pipeline.define_job(stage="echo")
def echo(c: Context):
    c.run("echo 'Hello hpipe!'")
