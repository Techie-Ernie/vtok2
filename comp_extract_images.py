import cv2
from comp_ocr import ocr
from frame_extraction import extract_score_frames


def _get_region(frame):
    return frame[30:70, 770:1150]  # union of both score crops


def _get_scores(frame):
    img1 = cv2.resize(frame[30:70, 770:860], None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    img2 = cv2.resize(frame[30:70, 1040:1150], None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    return ocr(img1), ocr(img2)


def extract_images(video_path, frame_interval=540, debug=False):
    return extract_score_frames(
        video_path, _get_scores, frame_interval, debug,
        get_region_fn=_get_region,
    )
