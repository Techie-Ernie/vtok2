import cv2
from vct_ocr import ocr_score
from frame_extraction import extract_score_frames

# Calibrated from Masters London 2026 broadcast (1920x1080).
# Two HUD modes with different score positions:
#   Buy-phase (team names + logos): left score x~827, right score x~1093
#   Gameplay / between-rounds:      left score x~767, right score x~1158
# Team logos appear at x~694 (PRX) and x~1166 (LEV) during buy-phase only.
# Crops cover both score positions while excluding both logos.
_L = (5, 65, 720, 870)    # left-team score: take rightmost digit
_R = (5, 65, 1060, 1185)  # right-team score: take leftmost (logo is to the right in buy-phase)


def _get_region(frame):
    y0, y1, x0, x1 = _L
    left = frame[y0:y1, x0:x1]
    y0, y1, x0, x1 = _R
    right = frame[y0:y1, x0:x1]
    return cv2.hconcat([left, right])


def _get_scores(frame):
    y0, y1, x0, x1 = _L
    s1 = ocr_score(cv2.resize(frame[y0:y1, x0:x1], None, fx=2, fy=2), take="right")
    y0, y1, x0, x1 = _R
    s2 = ocr_score(cv2.resize(frame[y0:y1, x0:x1], None, fx=2, fy=2), take="left")
    if s1 == "100" and s2 == "100":
        return None, None
    return s1, s2


def vct_extract_images(video_path, frame_interval=540, debug=False, game_num=None):
    return extract_score_frames(
        video_path, _get_scores, frame_interval, debug,
        allow_swap=True, get_region_fn=_get_region, game_num=game_num,
    )


if __name__ == "__main__":
    vct_extract_images("output.mp4")
