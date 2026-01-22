from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jobs import create_job, get_job
from worker import run_m2m_pipeline
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}



UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 🔹 Wake-up endpoint
@app.get("/ping")
def ping():
    return {"status": "ok", "message": "server awake"}

# 🔹 Submit audio file
@app.post("/submit/file")
async def submit_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file.filename.endswith((".mp3", ".wav")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    job_id = create_job()

    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    with open(input_path, "wb") as f:
        f.write(await file.read())

    background_tasks.add_task(run_m2m_pipeline, job_id, input_path)

    return {
        "job_id": job_id,
        "status": "queued"
    }

# 🔹 Poll status
@app.get("/status/{job_id}")
def status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# 🔹 Get result
@app.get("/result/{job_id}")
def result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Job not completed")
    return job["result"]



