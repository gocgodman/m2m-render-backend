import time

JOBS = {}

def create_job():
    job_id = str(int(time.time() * 1000))
    JOBS[job_id] = {
        "status": "queued",
        "step": "queued",
        "progress": 0.0,
        "message": "Job created",
        "result": None,
        "error": None,
    }
    return job_id

def update_job(job_id, **kwargs):
    if job_id in JOBS:
        JOBS[job_id].update(kwargs)

def get_job(job_id):
    return JOBS.get(job_id)
