import configparser
import json
import os
import queue
import threading
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

app = Flask(__name__)

_jobs: dict[str, dict] = {}
_CLIPS_DIR = Path(__file__).parent


def read_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return {
        "debug_mode": config.getboolean("General", "debug"),
        "log_level": config.get("General", "log_level"),
        "interval": int(config.get("RoundDetection", "interval")),
        "minimum_kills": int(config.get("Highlights", "minimum_kills")),
    }


def _run_job(job_id: str, mode: str, params: dict):
    q = _jobs[job_id]["queue"]
    log = lambda msg: q.put({"type": "log", "message": msg})

    try:
        config = read_config()

        if mode == "vct":
            from pipeline import run_vct_pipeline
            run_vct_pipeline(
                youtube_url=params["youtube_url"],
                stats_link=params["stats_link"],
                start_time=params.get("start_time") or None,
                end_time=params.get("end_time") or None,
                config=config,
                log=log,
                subs=params.get("subs", True),
                game_num=int(params.get("game_num", 1)),
            )
        elif mode == "comp":
            from pipeline import run_comp_pipeline
            run_comp_pipeline(
                youtube_url=params["youtube_url"],
                player_id=params["player_id"],
                config=config,
                log=log,
            )
        else:
            log(f"Unknown mode: {mode}")
            q.put({"type": "done", "status": "error"})
            return

        q.put({"type": "done", "status": "ok"})
    except Exception as exc:
        log(f"Error: {exc}")
        q.put({"type": "done", "status": "error"})
    finally:
        _jobs[job_id]["running"] = False


@app.post("/api/run")
def api_run():
    data = request.get_json(force=True)
    mode = data.get("mode")
    if mode not in ("vct", "comp"):
        return jsonify({"error": "mode must be 'vct' or 'comp'"}), 400

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"queue": queue.Queue(), "running": True}
    t = threading.Thread(target=_run_job, args=(job_id, mode, data), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


@app.get("/api/status/<job_id>")
def api_status(job_id):
    if job_id not in _jobs:
        return jsonify({"error": "not found"}), 404

    def generate():
        q = _jobs[job_id]["queue"]
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("type") == "done":
                    break
            except queue.Empty:
                yield "data: {\"type\": \"ping\"}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/clips")
def api_clips():
    clips = sorted(
        str(p.name) for p in _CLIPS_DIR.glob("video*_final.mp4")
    )
    return jsonify(clips)


@app.get("/clips/<path:filename>")
def serve_clip(filename):
    return send_from_directory(_CLIPS_DIR, filename)


@app.get("/")
def index():
    return send_from_directory("templates", "index.html")


if __name__ == "__main__":
    app.run(port=5173, debug=True, threaded=True)
