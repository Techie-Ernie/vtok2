import configparser
import time
import datetime
from youtube_download import download_youtube
from extract_images import extract_images
from extract_video import convert_rounds, extract_clip
from scraper import scrape_stats
from edit import edit_video, get_predictions

start_time = time.time()

def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    debug_mode = config.getboolean('General', 'debug')
    log_level = config.get('General', 'log_level')
    interval = int(config.get('RoundDetection', 'interval'))
    minimum_kills = int(config.get('Highlights', 'minimum_kills'))
    config_values = {
        'debug_mode' : debug_mode,
        'log_level' : log_level,
        'interval' : interval,
        'minimum_kills' : minimum_kills,
    }
    print(config_values)
    return config_values

filename = download_youtube(input("YouTube URL: "))
stats_link = input("Stats link (valorant.op.gg)")

if filename and stats_link:
    config = read_config()
    highlights_dict = scrape_stats(stats_link, config['minimum_kills'])
    if highlights_dict:
        score_dict = extract_images(filename, frame_interval=config['interval'])
        
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
                