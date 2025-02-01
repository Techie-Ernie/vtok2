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

start_time = time.time()
subs = True

assert os.environ.get("API_KEY") is not None, "No API KEY!"


def read_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    debug_mode = config.getboolean("General", "debug")
    log_level = config.get("General", "log_level")
    interval = int(config.get("RoundDetection", "interval"))
    minimum_kills = int(config.get("Highlights", "minimum_kills"))
    config_values = {
        "debug_mode": debug_mode,
        "log_level": log_level,
        "interval": interval,
        "minimum_kills": minimum_kills,
    }
    print(config_values)
    return config_values


vct_or_comp = input("VCT/COMP: ")
filename = download_youtube(input("YouTube URL: "))

if vct_or_comp == "COMP":

    # stats_link = input("Stats link (valorant.op.gg)")
    player_id = input("Player ID: ")
    score = check_score(filename)
    print(score)
    map_name = predict_map_name(filename)
    print(map_name)
    stats_link = search_score(map_name, player_id, score)

    if filename and stats_link:
        config = read_config()
        highlights_dict = comp_scrape_stats(stats_link, config["minimum_kills"])
        if highlights_dict:
            score_dict = extract_images(filename, frame_interval=config["interval"])

            round_dict = convert_rounds(score_dict)
            if round_dict:
                video_count = extract_clip(filename, round_dict, highlights_dict)
                print(video_count)
                for i in range(video_count):
                    print(i)
                    pred = get_predictions(f"video{i}.mp4", debug=False)
                    comp_edit_video(predictions=pred, video_path=f"video{i}.mp4")
                    end_time = time.time()
                    time_taken = end_time - start_time
else:
    # We need to read the start time and end time for the map
    # Also check if the stats link is valid
    start_time = input("Start time: (HH:MM:SS)")
    end_time = input("End time: (HH:MM:SS)")
    ffmpeg.input(filename, ss=start_time, to=end_time).output(
        "output.mp4", c="copy"
    ).run()

    stats_link = input("Stats link(rib.gg)")
    # Example link: https://www.rib.gg/series/paper-rex-vs-evil-geniuses-valorant-champions-2023/55475?match=124524&tab=rounds
    if filename and stats_link:
        config = read_config()
        highlights_dict = vct_scrape_stats(stats_link)
        score_dict = vct_extract_images(filename, frame_interval=config["interval"])
        print(score_dict)
        round_dict = convert_rounds(score_dict)
        if round_dict:
            video_count = extract_clip(filename, round_dict, highlights_dict)
            print(video_count)
        for i in range(video_count):
            vct_edit_video(f"video{i}.mp4")
        if subs:
            for i in range(video_count):
                video_clip = VideoFileClip(f"video{i}.mp4")
                audio_clip = video_clip.audio
                audio_clip.write_audiofile(f"video{i}" + ".mp3")
                srt_file = transcribe_audio(input_file=f"video{i}.mp3")
                add_subtitles(
                    f"video{i}" + ".mp3",
                    f"video{i}" + ".mp4",
                    srt_file,
                    f"video{i}_final.mp4",
                )
