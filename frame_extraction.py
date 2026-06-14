import cv2
import time


def is_valid_score_change(self_score, prev_self_score, enemy_score, prev_enemy_score):
    return (
        (int(self_score) - prev_self_score) == 1 and int(enemy_score) == prev_enemy_score
    ) or (
        (int(enemy_score) - prev_enemy_score) == 1 and int(self_score) == prev_self_score
    )


def extract_score_frames(
    video_path, get_scores_fn, frame_interval=540, debug=False, allow_swap=False
):
    """
    Step through video frames and build a score_dict mapping "A:B" -> timestamp (float seconds).
    get_scores_fn(frame) must return (score1, score2) as digit strings, or (None, None) on failure.
    allow_swap handles the VCT case where OCR occasionally reads the two scores in the wrong order.
    """
    start = time.time()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("error: cannot open video file")
        exit()

    fps = cap.get(cv2.CAP_PROP_FPS)
    added_frames = []
    score_dict = {"0:0": 0.0}
    frame_number = 0
    prev_s1 = 0
    prev_s2 = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_number > 0 and frame_number % frame_interval == 0:
            timestamp = frame_number / fps
            s1, s2 = get_scores_fn(frame)

            if debug:
                print(f"scores: {s1}:{s2}")

            if s1 is not None and s2 is not None and s1.isdigit() and s2.isdigit():
                if is_valid_score_change(s1, prev_s1, s2, prev_s2):
                    key = f"{s1}:{s2}"
                    if key not in added_frames:
                        added_frames.append(key)
                        score_dict[key] = timestamp
                        prev_s1, prev_s2 = int(s1), int(s2)
                elif allow_swap and is_valid_score_change(s2, prev_s1, s1, prev_s2):
                    key = f"{s2}:{s1}"
                    if key not in added_frames:
                        added_frames.append(key)
                        score_dict[key] = timestamp
                        prev_s1, prev_s2 = int(s2), int(s1)

        frame_number += 1

    cap.release()
    print(f"Extraction completed in {time.time() - start:.1f}s")
    return score_dict
