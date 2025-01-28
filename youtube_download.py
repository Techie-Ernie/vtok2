import yt_dlp


def download_youtube(url):

    # Configure options if necessary
    ydl_opts = {
        "outtmpl": "%(title)s.%(ext)s",
        "format": "bestvideo+bestaudio",  # Choose the best available quality
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename


if __name__ == "__main__":
    url = input("URL: ")
    download_youtube(url)


# ffmpeg -ss 00:10:01 -to 01:12:38 -i prxvsegpearl.mp4 -c copy output.mp4
