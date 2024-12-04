from moviepy import VideoFileClip, ffmpeg_tools

def convert_rounds(score_dict):
    round_dict = {}
    counter = 1
    for round, time in score_dict.items():
        round_dict[counter]=time
        counter += 1
    return round_dict
def extract_clip(vod_path, round_dict, highlights_dict):
    video_count = 0
    for i in  range(len(list(highlights_dict.keys()))):
        round = list(highlights_dict.keys())[i]
        print(type(round))
        start_time = round_dict[round]
        print(start_time)
        end_time = round_dict[round+1]
        print(end_time)
        
        with VideoFileClip(vod_path) as video:
            new = video.subclipped(start_time, end_time)
            new.write_videofile(f"video{i}.mp4")
        
        video_count += 1
    return video_count
    
            
if __name__ == "__main__":
    score_dict = {'0:0': 0.0, '1:0': 99.0, '2:0': 171.0, '3:0': 225.0, '4:0': 342.0, '5:0': 405.0, '6:0': 477.0, '6:1': 576.0, '7:1': 738.0, '8:1': 819.0, '8:2': 918.0, '9:2': 1053.0, '9:3': 1179.0, '10:3': 1188.0, '11:3': 1278.0, '11:4': 1404.0, '12:4': 1467.0, '12:5': 1539.0, '12:6': 1593.0, '12:7': 1692.0, '12:8': 1791.0, '12:9': 1935.0, '13:9': 2025.0}
    round_dict = convert_rounds(score_dict)
    extract_clip('/home/ernie/vtok2/TARIK PRO JETT VALORANT GAMEPLAY FULL MATCH VOD.mp4', round_dict, {2: 4})        
