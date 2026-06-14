import subprocess
import ffmpeg
from moviepy import VideoFileClip, CompositeVideoClip
import cv2
from inference_sdk import InferenceHTTPClient
import os


API_KEY = os.environ.get("API_KEY")


def get_predictions(video_path, debug=False):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("error: cannot open video file")
        exit()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 150)
    success, image = cap.read()
    if not success:
        return None
    cv2.imwrite("predictions_img.png", image)
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=API_KEY)
    result = CLIENT.infer("predictions_img.png", model_id="streamer-webcams/2")
    if not result.get("predictions"):
        return None

    if debug:
        image = cv2.imread("predictions_img.png")
        x, y, width, height = (
            result["predictions"][0]["x"],
            result["predictions"][0]["y"],
            result["predictions"][0]["width"],
            result["predictions"][0]["height"],
        )
        x1, y1 = int(x - width / 2), int(y - height / 2)
        cv2.rectangle(image, (x1, y1), (x1 + int(width), y1 + int(height)), (0, 255, 0), 2)
        cv2.imshow("Image with Bounding Box", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return result["predictions"][0]


def comp_edit_video(predictions, video_path, output_dir="videos/"):
    if predictions is None:
        print(f"no predictions found for {video_path}, skipping")
        return
    print(predictions)
    x = predictions["x"]
    y = predictions["y"]
    width = predictions["width"]
    height = predictions["height"]
    gameplay = VideoFileClip(video_path)
    streamer_cam = gameplay.cropped(x_center=x, y_center=y, width=width, height=height)
    gameplay = gameplay.resized(width=1080, height=1280)
    gameplay = gameplay.cropped(x1=400, x2=(gameplay.w - 400))
    streamer_cam = streamer_cam.resized(width=1080, height=640)
    streamer_cam = streamer_cam.with_position(("center", "top"))
    gameplay = gameplay.with_position(("center", "bottom"))
    final_clip = CompositeVideoClip([streamer_cam, gameplay], size=(1080, 1920))
    final_clip.write_videofile(
        f"{output_dir}/{os.path.splitext(video_path)[0]}_final.mp4",
        threads=12,
        preset="ultrafast",
    )


def vct_edit_video(input_path, output_path, srt_path=None):
    """
    Compose 9:16 short: blurred stretched background + centered gameplay overlay.
    Optionally burns SRT subtitles in the same ffmpeg pass — no intermediate files.

    Layout (1080×1920 canvas):
      - bg: source stretched to fill 1080×1920, blurred
      - fg: center 1080×1080 crop of source, overlaid at y=420
    """
    sub_filter = ""
    if srt_path:
        escaped = srt_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        sub_filter = f",subtitles='{escaped}'"

    filter_complex = (
        "[0:v]scale=1080:1920:flags=bilinear,boxblur=20:1,setsar=1[bg];"
        "[0:v]crop=1080:1080:400:0,setsar=1[fg];"
        f"[bg][fg]overlay=x=0:y=420{sub_filter}[out]"
    )

    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path,
         "-filter_complex", filter_complex,
         "-map", "[out]", "-map", "0:a",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         output_path],
        check=True,
    )


if __name__ == "__main__":
    vct_edit_video("video0.mp4", overlay=True)
