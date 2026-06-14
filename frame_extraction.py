import cv2
import time


def is_valid_score_change(self_score, prev_self_score, enemy_score, prev_enemy_score):
    return (
        (int(self_score) - prev_self_score) == 1 and int(enemy_score) == prev_enemy_score
    ) or (
        (int(enemy_score) - prev_enemy_score) == 1 and int(self_score) == prev_self_score
    )


_DIFF_THRESHOLD = 3.0  # mean absolute pixel diff below which the score region is considered unchanged


def extract_score_frames(
    video_path, get_scores_fn, frame_interval=540, debug=False, allow_swap=False,
    get_region_fn=None, game_num=None,
):
    """
    Step through video frames and build a score_dict mapping "A:B" -> timestamp (float seconds).
    get_scores_fn(frame) must return (score1, score2) as digit strings, or (None, None) on failure.
    allow_swap handles the VCT case where OCR occasionally reads the two scores in the wrong order.
    get_region_fn(frame), if provided, returns the raw score-region crop used for a cheap pixel-diff
    pre-filter that skips OCR when the region hasn't visibly changed since the last sample.
    game_num, if set, tracks map boundaries (score resetting to 0:0 after being non-zero) and only
    records timestamps for the Nth map in the video; timestamps remain absolute.
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
    prev_region = None
    ocr_calls = 0
    current_map = 1

    while cap.isOpened():
        if not cap.grab():
            break
        frame_number += 1

        if frame_number % frame_interval != 0:
            continue

        ret, frame = cap.retrieve()
        if not ret:
            continue

        timestamp = frame_number / fps

        # Cheap pixel-diff pre-filter: skip OCR if the score region looks the same
        if get_region_fn is not None:
            region = get_region_fn(frame)
            if prev_region is not None and cv2.absdiff(region, prev_region).mean() < _DIFF_THRESHOLD:
                continue
            prev_region = region

        ocr_calls += 1
        s1, s2 = get_scores_fn(frame)

        if debug:
            print(f"frame {frame_number} t={timestamp:.1f}s  scores: {s1}:{s2}  (ocr call #{ocr_calls})")

        if s1 is not None and s2 is not None and s1.isdigit() and s2.isdigit():
            s1_int, s2_int = int(s1), int(s2)

            # Detect map boundary: score returns to 0:0 after having been non-zero.
            # prev_s1/prev_s2 are always tracked (even for non-target maps) so this fires correctly.
            if game_num is not None and (prev_s1 > 0 or prev_s2 > 0) and s1_int == 0 and s2_int == 0:
                current_map += 1
                prev_s1, prev_s2 = 0, 0
                added_frames = []
                prev_region = None
                if current_map == game_num:
                    score_dict = {"0:0": timestamp}
                elif current_map > game_num:
                    break
                if debug:
                    print(f"  → map boundary detected, now on map {current_map}")
                continue

            in_target = (game_num is None or current_map == game_num)

            if is_valid_score_change(s1, prev_s1, s2, prev_s2):
                if in_target:
                    key = f"{s1}:{s2}"
                    if key not in added_frames:
                        added_frames.append(key)
                        score_dict[key] = timestamp
                prev_s1, prev_s2 = s1_int, s2_int
            elif allow_swap and is_valid_score_change(s2, prev_s1, s1, prev_s2):
                if in_target:
                    key = f"{s2}:{s1}"
                    if key not in added_frames:
                        added_frames.append(key)
                        score_dict[key] = timestamp
                prev_s1, prev_s2 = int(s2), int(s1)

    cap.release()
    print(f"Extraction completed in {time.time() - start:.1f}s ({ocr_calls} OCR calls)")
    return score_dict
