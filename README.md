# VTok 2.0

#### Extract highlights from pro players' VALORANT games and convert them into TikTok-friendly videos

### Example

[Original VOD Link](https://www.youtube.com/watch?v=dWUe6yjbxv4)

[![Original VOD Link](https://img.youtube.com/vi/dWUe6yjbxv4/0.jpg)](https://www.youtube.com/watch?v=dWUe6yjbxv4)

[CLIP_EXTRACTED](https://youtu.be/ONbc8BVhpTc)

[![CLIP_EXTRACTED](https://img.youtube.com/vi/ONbc8BVhpTc/0.jpg)](https://www.youtube.com/watch?v=ONbc8BVhpTc)

[TikTok-friendly video](https://youtube.com/shorts/a5YGxXdjkdA?si=DLSR78TdzJAEgvlm)

[![Tiktok-friendly video](https://img.youtube.com/vi/a5YGxXdjkdA/0.jpg)](https://www.youtube.com/watch?v=a5YGxXdjkdA)

### Prerequisities

- This project has been developed and tested on **Ubuntu 22.04 (WSL)**. A Linux distribution is preferred to run the program. Future updates will include Windows support.
- An account on [Roboflow](roboflow.com) to use the [model](https://universe.roboflow.com/clipsfail/streamer-webcams) for detection of the streamer's camera. Visit [app.roboflow.com](app.roboflow.com), go to settings and copy the Private API Key

- Set the API_KEY environment variable:

```
export API_KEY=YOUR_ROBOFLOW_API_KEY
```

- Python 3.9 or greater

### Installation (full installation guide coming soon!)

1. Clone the repository

    ```bash
    git clone https://github.com/Techie-Ernie/vtok2.git
    ```

2. Install requirements

    ```bash
    cd vtok2
    pip install -r requirements.txt
    ```

3. Run main.py and provide links to the match stats (valorant.op.gg) and to the match VOD (only YouTube links supported for now). Further configuration can be done by editing config.ini

    ```
    python main.py
    ```

4. The videos will be placed in the videos/ folder as video{x}_final.mp4. The original clips can be found in the vtok2 folder as video{x}.mp4. Will add option to remove these temporary files in a future update.

### How it works

#### Explanation of each script

1. **youtube_download.py**

- Uses the yt_dlp library to download the video from the YouTube link the user has provided

2. **scraper.py**

- Contains the scrape_stats() function, which uses Selenium to count the number of kills in each round. This returns a dict highlight_rounds, which are the rounds where kills >= MIN_KILLS (as defined in config.ini)

3. **extract_images.py**

- Contains the extract_images() function which takes in the downloaded video and reads the frames using OpenCV, skipping forward by frame_interval (as defined in config.ini) number of frames.
- PaddleOCR is used to read the numbers corresponding to the player's team score and the opponent's score, adding it to score_dict, along with its timestamp. Identical scores and scores which don't make sense (e.g. from 10-7 to 10-6) will not be added.
- score_dict is returned
- This part is still buggy, as contrast between the numbers and the background is sometimes too low and the numbers are inaccurate or not recognised.

4. **extract_video.py**

- convert_rounds() takes in the score_dict from extract_images() and simply iterates through score_dict to replace the key (initially something like '0:0' in score_dict to '1' instead - essentially getting the round number). The new dict returned is round_dict
- extract_clip() parses the round_dict and highlight_dict in order to determine the timestamps where there are highlights that need to be extracted. It then uses moviepy to extract a subclip of the original downloaded video and writes the subclip to a file. The result will look like the CLIP_EXTRACTED video at the top of this file.

5. **edit.py**

- edit.py converts the video into a TikTok-friendly format.
- get_predictions() uses a model from Roboflow to detect the streamer's camera in a particular frame of the video. (set to 150th frame - an arbitary number - check predictions_img.png if the function fails - may fix this later)
- The model locates the bounding box of the streamer's camera and these coordinates are sent to the edit_video() function
- edit_video() uses moviepy to create the final TikTok-friendly video by combining the streamer's camera at the top of the video and the gameplay at the bottom.

6.**find_match_stats.py**

- Finds the link to the match stats on valorant.op.gg by checking the last frames of the downloaded video to find the final match score.
- As many VODs of the games (on YouTube) have the map name in their titles, it checks for that. If not able to find the map name, you will have to key in the name manually.
- Input the Riot ID of the player
- Selenium is used to find the match (searches past 20 matches) : if it can't find the match, you will have to key the link in manually.

### Considerations

1. **Why use valorant.op.gg and not tracker.gg / blitz.gg?**

- Unfortunately, tracker.gg blocks web scrapers and blitz.gg does not provide enough information for the program to extract. While I would have preferred to use tracker.gg for convenience, valorant.op.gg was the only suitable option I found that provided stats which I could scrape with Selenium.

2. **Why PaddleOCR instead of EasyOCR, pytesseract, etc?**

- I've tested with EasyOCR, pytesseract, PaddleOCR, keras-OCR, but PaddleOCR produced the most accurate results. EasyOCR often failed recognising single digits. As mentioned above, the detection is still not perfect and I'll be working on improving it.

3. **Adding subtitles**

- You can add subtitles by feeding the output videos from this program into [autosub](https://github.com/Techie-Ernie/autosub). It uses faster-whisper and moviepy to generate subtitles and burn them into the video.

4. **Moviepy is slow**

- From testing, moviepy takes rather long (about 5 minutes, not more than 10 minutes) to render a ~1 min video.
- However, I haven't found a way to fix this. Perhaps using the ffmpeg_tools directly in the moviepy library may work better (will try in the future)

### Future updates

- More customisation options in config.ini
- Integrating the original [VTOK 1.0](https://github.com/Techie-Ernie/vtok) into this new version - will need to update moviepy as well since VTOK 1.0 used moviepy 1.x, which has been updated to 2.x + support for VCT matches (however, vlr.gg and valorant.op.gg don't currently provide the stats I need, and rib.gg has shut down)
- Better OCR accuracy
- Support for Twitch vods on top of YouTube
- ~~Finding the match stats on valorant.op.gg directly from the YouTube video~~ **Added on 5/12/24**
