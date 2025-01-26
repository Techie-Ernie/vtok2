import configparser
import time
import os
from youtube_download import download_youtube
from comp_extract_images import extract_images
from comp_extract_video import convert_rounds, extract_clip
from scraper import scrape_stats
from comp_edit import edit_video, get_predictions
from comp_find_match_stats import predict_map_name, check_score, search_score

start_time = time.time()

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


filename = download_youtube(input("YouTube URL: "))

vct_or_comp = input("VCT/COMP: ")
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
        highlights_dict = scrape_stats(stats_link, config["minimum_kills"])
        if highlights_dict:
            score_dict = extract_images(filename, frame_interval=config["interval"])

            round_dict = convert_rounds(score_dict)
            if round_dict:
                video_count = extract_clip(filename, round_dict, highlights_dict)
                print(video_count)
                for i in range(video_count):
                    print(i)
                    pred = get_predictions(f"video{i}.mp4", debug=False)
                    edit_video(predictions=pred, video_path=f"video{i}.mp4")
                    end_time = time.time()
                    time_taken = end_time - start_time
else:
    stats_link = input("Stats link(rib.gg)")
