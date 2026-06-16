"""
Core processing pipelines for VCT and COMP modes.
Each function accepts a log() callback so progress can be streamed
to a web client or printed to the terminal.
"""
import os
import subprocess
import uuid
import ffmpeg

from youtube_download import download_youtube
from comp_extract_images import extract_images
from extract_video import convert_rounds, extract_clip
from scraper import comp_scrape_stats, vct_scrape_stats, vlr_scrape_stats, vlr_to_rib
from edit import comp_edit_video, get_predictions, vct_edit_video
from comp_find_match_stats import predict_map_name, check_score, search_score
from vct_extract_images import vct_extract_images, vct_extract_images_all
from subtitles import transcribe_audio
from upload import upload_video


# In-process cache keyed by scan_id: {"filename": str, "all_maps": {map_num: score_dict}}
_scan_cache: dict[str, dict] = {}


def _ensure_h264(filename, log=print):
    """Re-encode to H.264 if the video uses a codec OpenCV can't decode (e.g. AV1)."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", filename],
        capture_output=True, text=True
    )
    codec = result.stdout.strip()
    if codec and codec not in ("h264", "hevc", "mpeg4", "vp9"):
        log(f"Video is {codec} — transcoding to H.264 (this may take a while)...")
        out = filename.rsplit(".", 1)[0] + "_h264.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", filename, "-c:v", "libx264", "-preset", "fast",
             "-crf", "18", "-c:a", "copy", out],
            check=True
        )
        log(f"Transcoded to {out}")
        return out
    return filename


def _scrape(stats_link, stats_map_num, log, min_kills=4):
    """Scrape highlights + vocabulary from a rib.gg or vlr.gg URL."""
    if "vlr.gg" in stats_link:
        rib_link = vlr_to_rib(stats_link)
        if rib_link:
            log(f"Found on rib.gg: {rib_link}")
            return vct_scrape_stats(rib_link, map_index=stats_map_num, min_kills=min_kills)
        log("Not found on rib.gg — using vlr.gg scraper.")
        return vlr_scrape_stats(stats_link, stats_map_num)
    return vct_scrape_stats(stats_link, map_index=stats_map_num, min_kills=min_kills)


def pre_scan_vct(youtube_url, config, log=print):
    """
    Download and scan a VCT VOD for map boundaries.
    Caches the per-map score dicts so run_vct_pipeline_multi can skip re-scanning.
    Returns (scan_id, map_meta_list) where each meta dict contains:
      vod_map_num, start_time (HH:MM:SS), round_count, final_score
    """
    log("Downloading video...")
    filename = download_youtube(youtube_url)
    log(f"Downloaded: {filename}")
    filename = _ensure_h264(filename, log)

    log("Scanning video for map boundaries (this may take several minutes)...")
    all_maps = vct_extract_images_all(filename, frame_interval=config["interval"])
    log(f"Scan complete — found {len(all_maps)} map(s)")

    scan_id = str(uuid.uuid4())
    _scan_cache[scan_id] = {"filename": filename, "all_maps": all_maps}

    map_meta = []
    for map_num, score_dict in sorted(all_maps.items()):
        start_ts = list(score_dict.values())[0]
        rounds = len(score_dict) - 1  # exclude the initial "0:0" entry
        final_score = list(score_dict.keys())[-1]
        h = int(start_ts // 3600)
        m = int((start_ts % 3600) // 60)
        s = int(start_ts % 60)
        map_meta.append({
            "vod_map_num": map_num,
            "start_time": f"{h}:{m:02d}:{s:02d}",
            "round_count": rounds,
            "final_score": final_score,
        })

    return scan_id, map_meta


def run_vct_pipeline_multi(scan_id, map_configs, config, log=print, subs=True):
    """
    Extract and edit highlight clips for multiple maps from a pre-scanned VOD.
    scan_id must match one returned by pre_scan_vct.
    map_configs: list of {vod_map_num, stats_link, stats_map_num}
    """
    cached = _scan_cache.get(scan_id)
    if not cached:
        log("Scan not found — please re-scan the video first.")
        return

    filename = cached["filename"]
    all_maps = cached["all_maps"]
    total_clips = 0

    for cfg in map_configs:
        vod_map_num = int(cfg["vod_map_num"])
        stats_link = cfg.get("stats_link", "").strip()
        stats_map_num = int(cfg.get("stats_map_num", 1))

        log(f"=== Map {vod_map_num} ===")

        if not stats_link:
            log(f"No stats link — skipping map {vod_map_num}")
            continue
        if vod_map_num not in all_maps:
            log(f"Map {vod_map_num} not in scan results — skipping")
            continue

        log("Scraping highlights...")
        highlights_dict, vocabulary = _scrape(stats_link, stats_map_num, log, min_kills=config["minimum_kills"])
        log(f"Highlight rounds: {list(highlights_dict.keys())}")
        if not highlights_dict:
            log("No highlights found — skipping")
            continue

        round_dict = convert_rounds(all_maps[vod_map_num])
        if not round_dict:
            log("No rounds detected — skipping")
            continue

        prefix = f"map{vod_map_num}_"
        log("Extracting clips...")
        video_count = extract_clip(filename, round_dict, highlights_dict, prefix=prefix)
        log(f"Extracted {video_count} clip(s)")

        for i in range(video_count):
            clip_in = f"{prefix}video{i}.mp4"
            clip_out = f"{prefix}video{i}_final.mp4"
            log(f"Editing {clip_in}...")
            srt_path = None
            if subs:
                log(f"Transcribing {clip_in}...")
                srt_path = transcribe_audio(clip_in, words=True, gpu=False, vocabulary=vocabulary)
            vct_edit_video(clip_in, clip_out, srt_path=srt_path)
            log(f"Ready → {clip_out}")
            total_clips += 1

    if total_clips > 0:
        log("Uploading to Google Drive...")
        upload_video(name_filter="final")

    log(f"All done — {total_clips} clip(s) produced.")


def run_vct_pipeline_auto(youtube_url, stats_links, start_time, end_time,
                          config, log=print, subs=True):
    """
    Fully-automated VCT pipeline.
    stats_links: list of {stats_link, stats_map_num} in map order.
    Scans the entire VOD once, then matches each entry positionally to the
    detected maps (1st entry → map 1, 2nd → map 2, …).
    """
    log("Downloading video...")
    filename = download_youtube(youtube_url)
    log(f"Downloaded: {filename}")
    filename = _ensure_h264(filename, log)

    if start_time and end_time:
        log(f"Trimming to {start_time} – {end_time}...")
        ffmpeg.input(filename, ss=start_time, to=end_time).output("output.mp4", c="copy").run()
        filename = "output.mp4"

    log("Scanning video for map boundaries...")
    all_maps = vct_extract_images_all(filename, frame_interval=config["interval"])
    log(f"Scan complete — {len(all_maps)} map(s) found in video")

    use_prefix = len(stats_links) > 1
    total_clips = 0

    for i, cfg in enumerate(stats_links):
        vod_map_num = i + 1
        stats_link = cfg.get("stats_link", "").strip()
        stats_map_num = int(cfg.get("stats_map_num", 1))

        if not stats_link:
            log(f"Map {vod_map_num}: no stats link — skipping")
            continue
        if vod_map_num not in all_maps:
            log(f"Map {vod_map_num}: not found in scan ({len(all_maps)} map(s) detected) — skipping")
            continue

        if use_prefix:
            log(f"=== Map {vod_map_num} ===")

        log("Scraping highlights...")
        highlights_dict, vocabulary = _scrape(stats_link, stats_map_num, log, min_kills=config["minimum_kills"])
        log(f"Highlight rounds: {list(highlights_dict.keys())}")
        if not highlights_dict:
            log("No highlights found — skipping")
            continue

        round_dict = convert_rounds(all_maps[vod_map_num])
        if not round_dict:
            log("No rounds detected — skipping")
            continue

        prefix = f"map{vod_map_num}_" if use_prefix else ""
        log("Extracting clips...")
        video_count = extract_clip(filename, round_dict, highlights_dict, prefix=prefix)
        log(f"Extracted {video_count} clip(s)")

        for j in range(video_count):
            clip_in = f"{prefix}video{j}.mp4"
            clip_out = f"{prefix}video{j}_final.mp4"
            log(f"Editing {clip_in}...")
            srt_path = None
            if subs:
                log(f"Transcribing {clip_in}...")
                srt_path = transcribe_audio(clip_in, words=True, gpu=False, vocabulary=vocabulary)
            vct_edit_video(clip_in, clip_out, srt_path=srt_path)
            log(f"Ready → {clip_out}")
            total_clips += 1

    if total_clips > 0:
        log("Uploading to Google Drive...")
        upload_video(name_filter="final")

    log(f"All done — {total_clips} clip(s) produced.")


def run_vct_pipeline(youtube_url, stats_link, start_time, end_time,
                     config, log=print, subs=True, game_num=1):
    log("Downloading video...")
    filename = download_youtube(youtube_url)
    log(f"Downloaded: {filename}")
    filename = _ensure_h264(filename, log)

    if start_time and end_time:
        log(f"Trimming to {start_time} – {end_time}...")
        ffmpeg.input(filename, ss=start_time, to=end_time).output("output.mp4", c="copy").run()
        filename = "output.mp4"

    log("Finding match highlights...")
    highlights_dict, vocabulary = _scrape(stats_link, game_num, log, min_kills=config["minimum_kills"])

    log(f"Highlight rounds: {list(highlights_dict.keys())}")
    if not highlights_dict:
        log("No highlight rounds found — aborting.")
        return

    log("Scanning video for round timestamps...")
    score_dict = vct_extract_images(filename, frame_interval=config["interval"], game_num=game_num)
    log(f"Detected {len(score_dict)} score changes")
    round_dict = convert_rounds(score_dict)
    if not round_dict:
        log("No rounds detected — aborting.")
        return

    log("Extracting clips...")
    video_count = extract_clip(filename, round_dict, highlights_dict)
    log(f"Extracted {video_count} clip(s)")

    if video_count == 0:
        log("No clips extracted — aborting.")
        return

    for i in range(video_count):
        log(f"Editing clip {i + 1}/{video_count}...")
        srt_path = None
        if subs:
            log(f"Transcribing clip {i + 1}/{video_count}...")
            srt_path = transcribe_audio(f"video{i}.mp4", words=True, gpu=False, vocabulary=vocabulary)
        vct_edit_video(f"video{i}.mp4", f"video{i}_final.mp4", srt_path=srt_path)
        log(f"Clip {i + 1} ready → video{i}_final.mp4")

    if subs:
        log("Uploading to Google Drive...")
        upload_video(name_filter="final")

    log("All done!")


def run_comp_pipeline(youtube_url, player_id, config, log=print):
    assert os.environ.get("API_KEY"), "API_KEY environment variable is not set"

    log("Downloading video...")
    filename = download_youtube(youtube_url)
    log(f"Downloaded: {filename}")

    log("Reading final score from video...")
    score = check_score(filename)
    log(f"Score detected: {score}")
    map_name = predict_map_name(filename)
    log(f"Map: {map_name}")

    log("Searching valorant.op.gg for match stats...")
    stats_link = search_score(map_name, player_id, score)
    if not stats_link:
        log("Match not found — aborting.")
        return

    log("Scraping per-round kill counts...")
    highlights_dict = comp_scrape_stats(stats_link, config["minimum_kills"])
    if not highlights_dict:
        log("No highlight rounds found.")
        return

    log(f"Highlight rounds: {highlights_dict}")

    log("Scanning video for round timestamps...")
    score_dict = extract_images(filename, frame_interval=config["interval"])
    round_dict = convert_rounds(score_dict)
    if not round_dict:
        log("No rounds detected — aborting.")
        return

    log("Extracting clips...")
    video_count = extract_clip(filename, round_dict, highlights_dict)
    log(f"Extracted {video_count} clip(s)")

    for i in range(video_count):
        log(f"Editing clip {i + 1}/{video_count}...")
        pred = get_predictions(f"video{i}.mp4", debug=False)
        comp_edit_video(predictions=pred, video_path=f"video{i}.mp4")
        log(f"Clip {i + 1} ready → video{i}_final.mp4")

    log("All done!")
