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
    if success:
        cv2.imwrite("predictions_img.png", image)
        CLIENT = InferenceHTTPClient(
            api_url="https://detect.roboflow.com", api_key=API_KEY
        )
        result = CLIENT.infer("predictions_img.png", model_id="streamer-webcams/2")
        if debug:
            image = cv2.imread("predictions_img.png")
            x, y, width, height = (
                result["predictions"][0]["x"],
                result["predictions"][0]["y"],
                result["predictions"][0]["width"],
                result["predictions"][0]["height"],
            )

            # Convert the center x, y, width, height to top-left corner x, y, width, height
            x1, y1 = int(x - width / 2), int(y - height / 2)

            # Draw the bounding box
            cv2.rectangle(
                image, (x1, y1), (x1 + int(width), y1 + int(height)), (0, 255, 0), 2
            )

            # Display image with bounding box for debugging
            cv2.imshow("Image with Bounding Box", image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return result["predictions"][0]


def edit_video(predictions, video_path, output_dir="."):
    # maybe don't write audio here to speed it up
    print(predictions)
    x = predictions["x"]
    y = predictions["y"]
    width = predictions["width"]
    height = predictions["height"]
    # Load gameplay video
    gameplay = VideoFileClip(video_path)

    streamer_cam = gameplay.cropped(x_center=x, y_center=y, width=width, height=height)
    gameplay = gameplay.resized(width=1080, height=1280)
    gameplay = gameplay.cropped(x1=400, x2=(gameplay.w - 400))
    streamer_cam = streamer_cam.resized(width=1080, height=640)
    streamer_cam = streamer_cam.with_position(("center", "top"))
    gameplay = gameplay.with_position(("center", "bottom"))
    final_clip = CompositeVideoClip([streamer_cam, gameplay], size=(1080, 1920))
    final_clip.write_videofile(
        f"{output_dir}/{os.path.splitext(video_path)[0]}_final.mp4"
    )
    # ffmpeg_write_video(final_clip, f'{output_dir}/{os.path.splitext(video_path)[0]}_final.mp4', fps=30)
    # f'{output_dir}/{os.path.splitext(video_path)[0]}.mp4'
    # final_clip.write_videofile(f"{output_dir}/{video_path.split('.')[0]}-final.mp4")


if __name__ == "__main__":
    video_path = input("video_path: ")
    pred = get_predictions(video_path)
    edit_video(pred, video_path)
