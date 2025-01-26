import cv2
import time
from comp_ocr import ocr


# Returns score dict
def extract_images(video_path, output_dir="images/", frame_interval=540, debug=False):
    start = time.time()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("error: cannot open video file")
        exit()
    fps = cap.get(cv2.CAP_PROP_FPS)
    # frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # getting total no. of frames
    added_frames = []
    score_dict = {}
    frame_number = 0

    # Add support for stretch res - test on PRX Jinggg gameplay
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        prev_self_score = 0
        prev_enemy_score = 0
        round = 0
        if frame_number % frame_interval == 0:
            timestamp = frame_number / fps
            timestamp_str = f"{timestamp:.2f}"
            if frame_number == 0:
                result_1 = "0"
                result_2 = "0"
            else:
                cropped_frame_1 = frame[30:70, 770:860]
                cropped_frame_2 = frame[30:70, 1050:1150]
                # output_path = os.path.join(output_dir, f"{timestamp_str}.png")
                img_1 = cv2.resize(
                    (cropped_frame_1), None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR
                )
                img_2 = cv2.resize(
                    (cropped_frame_2), None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR
                )
                result_1 = ocr(img_1)
                result_2 = ocr(img_2)
                if debug:
                    print(f"result1:{result_1}")
                    print(f"result2:{result_2}")
                    cv2.imwrite("file1.png", img_1)
                    cv2.imwrite("file2.png", img_2)
            count = 0
            result = [result_1, result_2]
            print(result)
            for item in result:
                if isinstance(item, str):
                    count += 1
            if count == 2:  # Check if there are 2 elements e.g. ['0', '0']
                self_score = result[0]
                enemy_score = result[1]
                if (
                    self_score.isdigit() and enemy_score.isdigit()
                ):  # Check both are valid integers
                    # can do some additional checking here to see if numbers make sense
                    if (
                        int(self_score) > prev_self_score
                        or int(enemy_score) > prev_enemy_score
                    ):
                        if f"{self_score}:{enemy_score}" not in added_frames:
                            added_frames.append(f"{self_score}:{enemy_score}")
                            score_dict[f"{self_score}:{enemy_score}"] = float(
                                timestamp_str
                            )
                            prev_self_score = int(self_score)
                            prev_enemy_score = int(enemy_score)
                            round += 1
        frame_number += 1
    end = time.time()
    print(
        f"Extraction completed in {end - start} seconds"
    )  # Time taken for prog to run
    cap.release()
    return score_dict
