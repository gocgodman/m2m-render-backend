import os
import time
import traceback
import subprocess
import re
from jobs import update_job

WORK_DIR = "/tmp/m2m"
os.makedirs(WORK_DIR, exist_ok=True)

# Transkun 진행률 정규식
PROGRESS_RE = re.compile(r'(\d+)\s*/\s*(\d+)')
PERCENT_RE  = re.compile(r'(\d+)\s*%')

def run_m2m_pipeline(job_id: str, input_audio_path: str):
    try:
        # ==================== Preprocessing ====================
        update_job(
            job_id,
            state="processing",
            step="preprocessing",
            progress=0.1,
            message="Preparing audio",
            eta_seconds=None
        )
        print(f"[{job_id}] Step: preprocessing, Progress: 0.1, Message: Preparing audio", flush=True)

        base = os.path.splitext(os.path.basename(input_audio_path))[0]
        midi_path = os.path.join(WORK_DIR, f"{base}.mid")
        wav_path = os.path.join(WORK_DIR, f"{base}_render.wav")

        # ==================== Transcribing ====================
        update_job(
            job_id,
            step="transcribing",
            progress=0.4,
            message="Running Transkun (MP3 → MIDI)",
            eta_seconds=None
        )
        print(f"[{job_id}] Step: transcribing, Progress: 0.4, Message: Running Transkun", flush=True)

        proc = subprocess.Popen(
            ["transkun", input_audio_path, midi_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        start_time = time.time()
        last_ratio = None

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue

            # 원래 Transkun 콘솔 출력 그대로 보여주기
            print(line, flush=True)

            # 진행률 계산
            ratio = None
            msg = None
            m = PROGRESS_RE.search(line)
            if m:
                cur, total = int(m.group(1)), int(m.group(2))
                ratio = cur / total
                msg = f"Transcribing audio ({cur}/{total})"

            p = PERCENT_RE.search(line)
            if p:
                ratio = int(p.group(1)) / 100.0
                msg = f"Transcribing audio ({p.group(1)}%)"

            if ratio is not None and ratio > 0.02:
                elapsed = time.time() - start_time
                eta = int(elapsed * (1 - ratio) / ratio)
                progress = 0.4 + ratio * 0.3

                update_job(
                    job_id,
                    progress=round(progress, 3),
                    message=msg,
                    eta_seconds=eta
                )

                # 서버 로그 실시간 퍼센트 바
                bar_len = 30
                filled_len = int(bar_len * ratio)
                bar = '█' * filled_len + '-' * (bar_len - filled_len)
                print(f"\r[{bar}] {int(ratio*100)}% | ETA: {eta}s", end='', flush=True)

                last_ratio = ratio

        proc.wait()
        print()  # 줄 바꿈

        if proc.returncode != 0:
            raise RuntimeError("Transkun process failed")

        # ==================== Rendering ====================
        update_job(
            job_id,
            step="rendering",
            progress=0.75,
            message="Rendering MIDI to WAV",
            eta_seconds=15
        )
        print(f"[{job_id}] Step: rendering, Progress: 0.75, Message: Rendering MIDI to WAV", flush=True)

        sf2_path = "/usr/share/sounds/sf2/FluidR3_GM.sf2"

        subprocess.run([
            "fluidsynth",
            "-ni",
            sf2_path,
            midi_path,
            "-F",
            wav_path,
            "-r",
            "44100"
        ], check=True)

        # ==================== Done ====================
        update_job(
            job_id,
            state="done",
            step="done",
            progress=1.0,
            message="Completed",
            eta_seconds=0,
            result={
                "midi_path": midi_path,
                "wav_path": wav_path
            }
        )
        print(f"[{job_id}] Step: done, Progress: 1.0, Message: Completed", flush=True)

    except Exception as e:
        update_job(
            job_id,
            state="error",
            step="error",
            progress=1.0,
            message="Pipeline failed",
            eta_seconds=None,
            error=str(e) + "\n" + traceback.format_exc()
        )
        print(f"[{job_id}] Pipeline failed: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
