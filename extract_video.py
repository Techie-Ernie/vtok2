from moviepy import VideoFileClip


def convert_rounds(score_dict):
    round_dict = {}
    counter = 1
    for round, time in score_dict.items():
        round_dict[counter] = time
        counter += 1
    return round_dict


def extract_clip(vod_path, round_dict, highlights_dict):
    print(f"Round dict: {round_dict}")
    video_count = 0
    for i in range(len(list(highlights_dict.keys()))):
        round = list(highlights_dict.keys())[i]
        print(type(round))
        try:
            start_time = round_dict[round]
            print(start_time)
            end_time = round_dict[round + 1]
            print(end_time)

            with VideoFileClip(vod_path) as video:
                new = video.subclipped(start_time, end_time)
                new.write_videofile(
                    f"video{i}.mp4",
                    threads=12,
                    preset="ultrafast",
                )

            video_count += 1
        except KeyError:  # when round_dict[round+1] gives an error at the last key
            break
    return video_count
