import cv2
import time


def is_valid_score_change(self_score, prev_self_score, enemy_score, prev_enemy_score):
    return (
        (int(self_score) - prev_self_score) == 1 and int(enemy_score) == prev_enemy_score
    ) or (
        (int(enemy_score) - prev_enemy_score) == 1 and int(self_score) == prev_self_score
    )


_DIFF_THRESHOLD = 3.0


def _extract_all_maps(
    video_path, get_scores_fn, frame_interval=540, debug=False,
    allow_swap=False, get_region_fn=None, stop_after=None,
):
    """
    Core scan loop. Always collects timestamps for every map found.
    Returns {map_num: score_dict} where score_dict maps "A:B" -> timestamp (float seconds).
    stop_after: stop as soon as this map's boundary is detected (skips scanning later maps).
    """
    t_start = time.time()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("error: cannot open video file")
        exit()

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_number = 0
    prev_s1 = 0
    prev_s2 = 0
    prev_region = None
    ocr_calls = 0
    current_map = 1
    added_frames = []
    all_maps = {1: {"0:0": 0.0}}

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

        if get_region_fn is not None:
            region = get_region_fn(frame)
            if prev_region is not None and cv2.absdiff(region, prev_region).mean() < _DIFF_THRESHOLD:
                continue
            prev_region = region

        ocr_calls += 1
        s1, s2 = get_scores_fn(frame)

        if debug:
            print(f"frame {frame_number} t={timestamp:.1f}s  scores: {s1}:{s2}  map={current_map}  (ocr #{ocr_calls})")

        if s1 is not None and s2 is not None and s1.isdigit() and s2.isdigit():
            s1_int, s2_int = int(s1), int(s2)

            if (prev_s1 > 0 or prev_s2 > 0) and s1_int == 0 and s2_int == 0:
                # Map boundary detected. If stop_after is set and we've just finished that map, bail.
                if stop_after is not None and current_map >= stop_after:
                    break
                current_map += 1
                prev_s1, prev_s2 = 0, 0
                added_frames = []
                prev_region = None
                all_maps[current_map] = {"0:0": timestamp}
                if debug:
                    print(f"  → map boundary, now on map {current_map}")
                continue

            score_dict = all_maps[current_map]

            if is_valid_score_change(s1, prev_s1, s2, prev_s2):
                key = f"{s1}:{s2}"
                if key not in added_frames:
                    added_frames.append(key)
                    score_dict[key] = timestamp
                prev_s1, prev_s2 = s1_int, s2_int
            elif allow_swap and is_valid_score_change(s2, prev_s1, s1, prev_s2):
                key = f"{s2}:{s1}"
                if key not in added_frames:
                    added_frames.append(key)
                    score_dict[key] = timestamp
                prev_s1, prev_s2 = int(s2), int(s1)

    cap.release()
    print(f"Extraction done in {time.time() - t_start:.1f}s ({ocr_calls} OCR calls, {len(all_maps)} map(s))")
    return all_maps


def extract_all_score_frames(
    video_path, get_scores_fn, frame_interval=540, debug=False,
    allow_swap=False, get_region_fn=None,
):
    """Scan entire video; return {map_num: score_dict} for every map detected."""
    return _extract_all_maps(
        video_path, get_scores_fn, frame_interval, debug, allow_swap, get_region_fn,
    )


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
    game_num, if set, stops scanning once that map's boundary is detected (saves time on long VODs).
    """
    all_maps = _extract_all_maps(
        video_path, get_scores_fn, frame_interval, debug, allow_swap, get_region_fn,
        stop_after=game_num,
    )
    if game_num is None:
        return all_maps.get(1, {"0:0": 0.0})
    return all_maps.get(game_num, {"0:0": 0.0})
