import os
import traceback
import subprocess
from jobs import update_job

# =========================
# 경로 설정
# =========================
BASE_WORK_DIR = "/tmp/m2m"
os.makedirs(BASE_WORK_DIR, exist_ok=True)

# =========================
# 핵심 파이프라인
# =========================
def run_m2m_pipeline(job_id: str, input_audio_path: str):
    job_dir = os.path.join(BASE_WORK_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        # 1️⃣ Preprocess
        update_job(
            job_id,
            state="processing",
            step="preprocessing",
            progress=0.1,
            message="Preparing audio"
        )

        base = os.path.splitext(os.path.basename(input_audio_path))[0]
        midi_path = os.path.join(job_dir, f"{base}.mid")
        wav_path = os.path.join(job_dir, f"{base}_render.wav")

        # 2️⃣ Transkun 실행
        update_job(
            job_id,
            step="transcribing",
            progress=0.4,
            message="Running Transkun (MP3 → MIDI)"
        )

        transkun_cmd = [
            "transkun",
            input_audio_path,
            midi_path
        ]

        subprocess.run(
            transkun_cmd,
            check=True,
            capture_output=True,
            text=True
        )

        # 3️⃣ MIDI 렌더링
        update_job(
            job_id,
            step="rendering",
            progress=0.75,
            message="Rendering MIDI to WAV"
        )

        sf2_path = "/usr/share/sounds/sf2/FluidR3_GM.sf2"

        subprocess.run(
            [
                "fluidsynth",
                "-ni",
                sf2_path,
                midi_path,
                "-F",
                wav_path,
                "-r",
                "44100"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        # 4️⃣ 완료
        update_job(
            job_id,
            state="completed",
            step="done",
            progress=1.0,
            message="Completed",
            result={
                "midi_path": midi_path,
                "wav_path": wav_path
            }
        )

    except subprocess.CalledProcessError as e:
        update_job(
            job_id,
            state="failed",
            step="error",
            progress=1.0,
            message="External command failed",
            error=e.stderr
        )

    except Exception as e:
        update_job(
            job_id,
            state="failed",
            step="error",
            progress=1.0,
            message="Pipeline failed",
            error=str(e) + "\n" + traceback.format_exc()
        )
