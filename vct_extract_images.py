import cv2
from vct_ocr import ocr
from frame_extraction import extract_score_frames, is_valid_score_change


def _get_scores(frame):
    img = cv2.resize(frame[0:70, 640:1290], None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    s1, s2 = ocr(img)
    if s1 == "100" and s2 == "100":
        return None, None
    return s1, s2


def vct_extract_images(video_path, frame_interval=540, debug=False):
    return extract_score_frames(video_path, _get_scores, frame_interval, debug, allow_swap=True)


if __name__ == "__main__":
    vct_extract_images("output.mp4")
