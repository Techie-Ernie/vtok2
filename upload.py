from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth
import os


def upload_video(folder=".", name_filter="video"):
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    for filename in os.listdir(folder):
        if os.path.splitext(filename)[1] == ".mp4" and name_filter in filename:
            metadata = {
                "parents": [{"id": "1-KURoYnlEt2_hiOubAGhWlPn6wS5Vnxb"}],
                "title": filename,
                "mimeType": "video/mp4",
            }
            file = drive.CreateFile(metadata=metadata)
            file.SetContentFile(filename)
            print("uploading video")
            file.Upload()


if __name__ == "__main__":
    upload_video(".")
