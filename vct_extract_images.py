import cv2
import time
from vct_ocr import ocr

# VCT EXTRACT IMAGES
# May require additional code since replays / timeouts show


def is_valid_score_change(self_score, prev_self_score, enemy_score, prev_enemy_score):
    if (
        (int(self_score) - prev_self_score) == 1
        and int(enemy_score) == prev_enemy_score
    ) or (
        (int(enemy_score) - prev_enemy_score) == 1
        and int(self_score) == prev_self_score
    ):
        return True
    return False


# Returns score dict
def vct_extract_images(
    video_path, output_dir="images/", frame_interval=540, debug=True
):
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
    prev_self_score = 0
    prev_enemy_score = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        round = 0
        if frame_number % frame_interval == 0:
            timestamp = frame_number / fps

            timestamp_str = f"{timestamp:.2f}"
            if frame_number == 0:
                result_1 = "0"
                result_2 = "0"
                score_dict["0:0"] = timestamp_str
            else:
                cropped_frame_1 = frame[0:70, 640:1290]
                # cropped_frame_2 = frame[0:100, 1000:1150]
                # output_path = os.path.join(output_dir, f"{timestamp_str}.png")
                img_1 = cv2.resize(
                    (cropped_frame_1), None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR
                )

                results = ocr(img_1)

                result_1 = results[0]
                result_2 = results[1]

                # result_2 = ocr(img_2)

                if debug:
                    print(f"result1:{result_1}")
                    print(f"result2:{result_2}")
                    cv2.imwrite("data/file1.png", img_1)

            count = 0

            if result_1 == "100" and result_2 == "100":
                print("Both none")
                # use ocr to check if it's replay/tech pause/halftime
                # need to update timestamp_str such that it skips this part
                # we can use time() and check the time since the last valid frames

            result = [result_1, result_2]
            print(result)
            for item in result:
                if isinstance(item, str):
                    count += 1
            # Clean up this chunk of code
            if count == 2:  # Check if there are 2 elements e.g. ['0', '0']

                self_score = result_1
                enemy_score = result_2
                if debug:
                    print(f"Previous self_score: {prev_self_score}")

                    print(f"Previous enemy score: {prev_enemy_score}")
                    print(f"Self score: {self_score}")
                    print(f"Enemy score: {enemy_score}")
                if (
                    self_score.isdigit() and enemy_score.isdigit()
                ):  # Check both are valid integers
                    # can do some additional checking here to see if numbers make sense

                    # If self_score is greater than previous_self_score, then enemy score has to be the same
                    # Similarly, if enemy_score is greater than previous_enemy_score, then self score has to be the same
                    if int(self_score) != 100 and int(enemy_score) != 100:
                        if is_valid_score_change(
                            self_score, prev_self_score, enemy_score, prev_enemy_score
                        ):
                            print("check succeeded")
                            if f"{self_score}:{enemy_score}" not in added_frames:
                                added_frames.append(f"{self_score}:{enemy_score}")
                                score_dict[f"{self_score}:{enemy_score}"] = float(
                                    timestamp_str
                                )
                                prev_self_score = int(self_score)
                                prev_enemy_score = int(enemy_score)
                                round += 1

                        elif is_valid_score_change(
                            enemy_score, prev_self_score, self_score, prev_enemy_score
                        ):
                            # Special case in which the OCR somehow reads the numbers swapped (e.g. 5:4 as 4:5)
                            print("check succeeded with swap")
                            if f"{enemy_score}:{self_score}" not in added_frames:
                                added_frames.append(f"{enemy_score}:{self_score}")
                                score_dict[f"{enemy_score}:{self_score}"] = float(
                                    timestamp_str
                                )
                                prev_self_score = int(enemy_score)
                                prev_enemy_score = int(self_score)
                            round += 1

                    else:
                        round += 1
        frame_number += 1
        # print(score_dict)

    end = time.time()
    print(
        f"Extraction completed in {end - start} seconds"
    )  # Time taken for prog to run
    cap.release()
    return score_dict


if __name__ == "__main__":
    vct_extract_images("output.mp4")
