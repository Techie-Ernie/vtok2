from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth
import os

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)


def upload_video(folder="."):
    print("function ran")
    for filename in os.listdir(folder):
        if os.path.splitext(filename)[1] == ".mp4" and "video" in filename:
            metadata = {
                "parents": [{"id": "1-KURoYnlEt2_hiOubAGhWlPn6wS5Vnxb"}],
                "title": f"{filename}",
                "mimeType": "video/mp4",
            }
            # Create file
            file = drive.CreateFile(metadata=metadata)
            file.SetContentFile(f"{filename}")
            print("uploading video")
            file.Upload()


if __name__ == "__main__":
    upload_video(".")
