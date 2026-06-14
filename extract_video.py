from moviepy import VideoFileClip


def convert_rounds(score_dict):
    return dict(enumerate(score_dict.values(), start=1))


def extract_clip(vod_path, round_dict, highlights_dict):
    print(f"Round dict: {round_dict}")
    video_count = 0
    for i, rnd in enumerate(highlights_dict.keys()):
        try:
            start_time = round_dict[rnd]
            end_time = round_dict[rnd + 1]
            with VideoFileClip(vod_path) as video:
                video.subclipped(start_time, end_time).write_videofile(
                    f"video{i}.mp4",
                    threads=12,
                    preset="ultrafast",
                )
            video_count += 1
        except KeyError:
            break
    return video_count
