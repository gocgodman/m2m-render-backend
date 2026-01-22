import os
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    BackgroundTasks,
    HTTPException
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from jobs import create_job, get_job
from worker import run_m2m_pipeline

# =========================
# FastAPI app
# =========================
app = FastAPI()

# =========================
# CORS 설정 (모든 origin 허용)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 헬스 체크 / 서버 깨우기
# =========================
@app.get("/ping")
def ping():
    return {"status": "ok"}

# =========================
# 파일 업로드 + Job 생성
# =========================
@app.post("/submit/file")
async def submit_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    # Job 생성
    job = create_job()
    job_id = job["job_id"]

    # Job 작업 디렉토리
    job_dir = f"/tmp/m2m/{job_id}"
    os.makedirs(job_dir, exist_ok=True)

    # 입력 파일 저장
    input_path = os.path.join(job_dir, file.filename)
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # 백그라운드 작업 등록
    background_tasks.add_task(
        run_m2m_pipeline,
        job_id,
        input_path
    )

    return {
        "job_id": job_id,
        "state": job["state"],
        "message": job["message"]
    }

# =========================
# Job 상태 조회
# =========================
@app.get("/status/{job_id}")
def status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# =========================
# 결과 파일 다운로드 (MIDI / WAV)
# =========================
@app.get("/download/{job_id}/{file_type}")
def download_result(job_id: str, file_type: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("state") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")

    result = job.get("result")
    if not result:
        raise HTTPException(status_code=404, detail="No result available")

    if file_type == "midi":
        path = result.get("midi_path")
        media_type = "audio/midi"
        filename = "output.mid"

    elif file_type == "wav":
        path = result.get("wav_path")
        media_type = "audio/wav"
        filename = "output.wav"

    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        media_type=media_type,
        filename=filename
    )
