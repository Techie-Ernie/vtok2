import configparser
import time
import ffmpeg
import os

from moviepy import VideoFileClip
from youtube_download import download_youtube
from comp_extract_images import extract_images
from extract_video import convert_rounds, extract_clip
from scraper import comp_scrape_stats, vct_scrape_stats
from edit import comp_edit_video, get_predictions, vct_edit_video
from comp_find_match_stats import predict_map_name, check_score, search_score
from vct_extract_images import vct_extract_images
from subtitles import transcribe_audio, add_subtitles
from upload import upload_video


def read_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return {
        "debug_mode": config.getboolean("General", "debug"),
        "log_level": config.get("General", "log_level"),
        "interval": int(config.get("RoundDetection", "interval")),
        "minimum_kills": int(config.get("Highlights", "minimum_kills")),
    }


def run_comp(filename):
    assert os.environ.get("API_KEY") is not None, "No API KEY!"
    player_id = input("Player ID: ")
    score = check_score(filename)
    print(score)
    map_name = predict_map_name(filename)
    print(map_name)
    stats_link = search_score(map_name, player_id, score)

    if not (filename and stats_link):
        return

    config = read_config()
    highlights_dict = comp_scrape_stats(stats_link, config["minimum_kills"])
    if not highlights_dict:
        return

    score_dict = extract_images(filename, frame_interval=config["interval"])
    round_dict = convert_rounds(score_dict)
    if not round_dict:
        return

    video_count = extract_clip(filename, round_dict, highlights_dict)
    print(video_count)
    for i in range(video_count):
        pred = get_predictions(f"video{i}.mp4", debug=False)
        comp_edit_video(predictions=pred, video_path=f"video{i}.mp4")


def run_vct(filename, subs=True):
    start_time_str = input("Start time: (HH:MM:SS) ")
    end_time_str = input("End time: (HH:MM:SS) ")
    ffmpeg.input(filename, ss=start_time_str, to=end_time_str).output(
        "output.mp4", c="copy"
    ).run()

    stats_link = input("Stats link(rib.gg) ")
    if not (filename and stats_link):
        return

    config = read_config()
    highlights_dict = vct_scrape_stats(stats_link)
    score_dict = vct_extract_images(filename, frame_interval=config["interval"])
    print(score_dict)
    round_dict = convert_rounds(score_dict)
    if not round_dict:
        return

    video_count = extract_clip(filename, round_dict, highlights_dict)
    print(video_count)
    for i in range(video_count):
        vct_edit_video(f"video{i}.mp4")

    if subs:
        for i in range(video_count):
            video_clip = VideoFileClip(f"video{i}_out.mp4")
            audio_clip = video_clip.audio
            audio_clip.write_audiofile(f"video{i}.mp3")
            srt_file = transcribe_audio(input_file=f"video{i}.mp3", words=True, gpu=False)
            add_subtitles(
                f"video{i}.mp3",
                f"video{i}_out.mp4",
                srt_file,
                f"video{i}_final.mp4",
            )
        upload_video(name_filter="final")


def main():
    start_time = time.time()
    vct_or_comp = input("VCT/COMP: ")
    filename = download_youtube(input("YouTube URL: "))

    if vct_or_comp == "COMP":
        run_comp(filename)
    else:
        run_vct(filename)

    print(f"Total time: {time.time() - start_time:.1f}s")


if __name__ == "__main__":
    main()
