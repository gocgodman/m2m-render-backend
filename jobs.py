import json
import os
import time

JOBS_DIR = "/tmp/m2m/jobs"
os.makedirs(JOBS_DIR, exist_ok=True)

def _job_path(job_id):
    return os.path.join(JOBS_DIR, f"{job_id}.json")

def create_job():
    job_id = str(int(time.time() * 1000))
    job = {
        "job_id": job_id,
        "state": "queued",
        "step": "queued",
        "progress": 0.0,
        "message": "Job created",
        "result": None,
        "error": None,
        "created_at": time.time()
    }
    with open(_job_path(job_id), "w") as f:
        json.dump(job, f)
    return job

def update_job(job_id, **kwargs):
    path = _job_path(job_id)
    if not os.path.exists(path):
        return
    with open(path) as f:
        job = json.load(f)
    job.update(kwargs)
    with open(path, "w") as f:
        json.dump(job, f)

def get_job(job_id):
    path = _job_path(job_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)




