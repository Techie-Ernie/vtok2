from moviepy import VideoFileClip


def convert_rounds(score_dict):
    round_dict = {}
    counter = 1
    for round, time in score_dict.items():
        round_dict[counter] = time
        counter += 1
    return round_dict


def extract_clip(vod_path, round_dict, highlights_dict):
    video_count = 0
    for i in range(len(list(highlights_dict.keys()))):
        round = list(highlights_dict.keys())[i]
        print(type(round))
        start_time = round_dict[round]
        print(start_time)
        end_time = round_dict[round + 1]
        print(end_time)

        with VideoFileClip(vod_path) as video:
            new = video.subclipped(start_time, end_time)
            new.write_videofile(f"video{i}.mp4")

        video_count += 1
    return video_count
