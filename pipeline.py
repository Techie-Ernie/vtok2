"""
Core processing pipelines for VCT and COMP modes.
Each function accepts a log() callback so progress can be streamed
to a web client or printed to the terminal.
"""
import os
import subprocess
import ffmpeg

from youtube_download import download_youtube
from comp_extract_images import extract_images
from extract_video import convert_rounds, extract_clip
from scraper import comp_scrape_stats, vct_scrape_stats, vlr_scrape_stats, vlr_to_rib
from edit import comp_edit_video, get_predictions, vct_edit_video
from comp_find_match_stats import predict_map_name, check_score, search_score
from vct_extract_images import vct_extract_images
from subtitles import transcribe_audio
from upload import upload_video


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
    vocabulary = []
    if "vlr.gg" in stats_link:
        rib_link = vlr_to_rib(stats_link)
        if rib_link:
            log(f"Found on rib.gg: {rib_link}")
            highlights_dict, vocabulary = vct_scrape_stats(rib_link)
        else:
            log("Not found on rib.gg — using vlr.gg scraper.")
            highlights_dict, vocabulary = vlr_scrape_stats(stats_link, game_num)
    else:
        highlights_dict, vocabulary = vct_scrape_stats(stats_link)

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
