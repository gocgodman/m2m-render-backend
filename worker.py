import os
import time
import traceback
import subprocess
import re
from jobs import update_job

WORK_DIR = "/tmp/m2m"
os.makedirs(WORK_DIR, exist_ok=True)

PROGRESS_RE = re.compile(r'(\d+)\s*/\s*(\d+)')
PERCENT_RE  = re.compile(r'(\d+)\s*%')

def run_m2m_pipeline(job_id: str, input_audio_path: str):
    try:
        update_job(
            job_id,
            state="processing",
            step="preprocessing",
            progress=0.1,
            message="Preparing audio",
            eta_seconds=None
        )

        base = os.path.splitext(os.path.basename(input_audio_path))[0]
        midi_path = os.path.join(WORK_DIR, f"{base}.mid")
        wav_path = os.path.join(WORK_DIR, f"{base}_render.wav")

        update_job(
            job_id,
            step="transcribing",
            progress=0.4,
            message="Running Transkun (MP3 → MIDI)",
            eta_seconds=None
        )

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
            line = line.strip()
            if not line:
                continue

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

                last_ratio = ratio

        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError("Transkun process failed")

        update_job(
            job_id,
            step="rendering",
            progress=0.75,
            message="Rendering MIDI to WAV",
            eta_seconds=15   # 대략 렌더링 예상
        )

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
