# VTok 2.0

#### Extract highlights from streamers' VALORANT games or VCT matches and convert them into TikTok-friendly videos

> [!IMPORTANT]
> VTok 2.0 is still under development, so bugs are to be expected.

### Example

[Original VOD Link](https://www.youtube.com/watch?v=dWUe6yjbxv4)

> [!Note]
> The program has been tested on videos from the YouTube channel [VALORANT Daily](https://www.youtube.com/@valorantdaily1976). Depending on how the videos posted on other channels, the program may or may not work without any further modification.

[![Original VOD Link](https://img.youtube.com/vi/dWUe6yjbxv4/0.jpg)](https://www.youtube.com/watch?v=dWUe6yjbxv4)

[CLIP_EXTRACTED](https://youtu.be/ONbc8BVhpTc)

[![CLIP_EXTRACTED](https://img.youtube.com/vi/ONbc8BVhpTc/0.jpg)](https://www.youtube.com/watch?v=ONbc8BVhpTc)

[TikTok-friendly video](https://youtube.com/shorts/a5YGxXdjkdA?si=DLSR78TdzJAEgvlm)

[![Tiktok-friendly video](https://img.youtube.com/vi/a5YGxXdjkdA/0.jpg)](https://www.youtube.com/watch?v=a5YGxXdjkdA)

### Prerequisites

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

3. Run main.py. Further configuration can be done by editing config.ini

    ```
    python main.py
    ```

4. The videos will be placed in the videos/ folder as video{x}_final.mp4. The original clips can be found in the vtok2 folder as video{x}.mp4. Will add option to remove these temporary files in a future update.

> [!TIP]
> For VCT mode, subtitles are automatically generated and burned into the final video using faster-whisper. No additional steps required.

### How it works

#### Explanation of each script

1. **youtube_download.py**

- Uses the yt_dlp library to download the video from the YouTube link the user has provided

2. **scraper.py**

- `comp_scrape_stats()` uses Selenium to count kills per round on valorant.op.gg, returning rounds where kills >= MIN_KILLS (config.ini).
- `vlr_scrape_stats(stats_link, game_num)` scrapes a vlr.gg match page with plain HTTP (no Selenium required). It reads elimination-type rounds from the match's round timeline and cross-references against the performance tab's advanced stats (4K/5K columns) to identify highlight rounds. Note: vlr.gg does not expose per-round kill counts in its HTML — multi-kill stats are only available as per-player aggregates per map, so all elimination rounds from maps with a 4K/5K are returned as the best approximation.
- Also exposes `make_stealth_driver()`, a shared helper for creating an anti-detection Chrome instance used by the COMP scrapers.

3. **edit.py**

- Converts the video into a TikTok-friendly format.
- `get_predictions()` uses a Roboflow model to detect the streamer's camera in frame 150 of the clip (check predictions_img.png if it fails). Returns `None` if no predictions are found.
- `comp_edit_video()` uses the predicted bounding box to crop the streamer cam and composites it above the gameplay in a 1080x1920 portrait layout.
- `vct_edit_video()` blurs the gameplay video as a background and overlays the original on top.

#### For streamers' games

4. **comp_extract_images.py**

- Contains `extract_images()`, which reads frames via OpenCV, skipping by `frame_interval` frames at a time.
- PaddleOCR reads the two score regions; results are validated by `frame_extraction.is_valid_score_change()` before being added to `score_dict`.
- OCR detection is still imperfect when contrast is low — check the extracted frames if results look wrong.

5. **frame_extraction.py**

- Shared frame-stepping loop used by both `comp_extract_images.py` and `vct_extract_images.py`.
- `is_valid_score_change()` checks that exactly one team's score increased by 1 and the other stayed the same.
- `extract_score_frames()` accepts a `get_scores_fn(frame)` callback and an `allow_swap` flag (used by VCT to handle OCR reading the two scores in the wrong order).

6. **extract_video.py**

- `convert_rounds()` re-keys `score_dict` from score strings (e.g. `'5:3'`) to round numbers (e.g. `6`).
- `extract_clip()` uses `round_dict` and `highlights_dict` to cut subclips from the original VOD with moviepy.

7. **comp_find_match_stats.py**

- Finds the match stats link on valorant.op.gg by reading the final score from the last frames of the downloaded video.
- Checks the video filename for a map name; prompts for manual input if not found.
- Uses Selenium (via `make_stealth_driver()` from `scraper.py`) to search recent matches by map and score. Falls back to manual input if no match is found.

#### For VCT matches

8. **vct_ocr.py**

- Uses EasyOCR to read both team scores from a single wide crop of the scoreboard. Returns `["100", "100"]` as a sentinel when no valid scores are detected.

9. **vct_extract_images.py**

- `vct_extract_images()` wraps `extract_score_frames()` with `allow_swap=True` to handle the occasional case where EasyOCR reads the two scores in the wrong order.
- Crops the entire top bar of the screen (including team names and timer) rather than just the score digits, which gives better EasyOCR accuracy.

10. **upload.py**

- `upload_video()` authenticates with Google Drive and uploads all `.mp4` files matching a name filter (default `"video"`). In VCT mode, `main.py` calls it with `name_filter="final"` to upload only the finished output files.

### Considerations

1. **Why use [valorant.op.gg](https://valorant.op.gg) and not [tracker.gg](https://tracker.gg/valorant) / [blitz.gg](https://blitz.gg)?**

- Unfortunately, tracker.gg blocks web scrapers and blitz.gg does not provide enough information for the program to extract. While I would have preferred to use tracker.gg for convenience, valorant.op.gg was the only suitable option I found that provided stats which I could scrape with Selenium.

2. **Why [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) instead of [EasyOCR](https://github.com/JaidedAI/EasyOCR), [pytesseract](https://github.com/madmaze/pytesseract), etc?**

- I've tested with EasyOCR, pytesseract, PaddleOCR, keras-OCR, but PaddleOCR produced the most accurate results. EasyOCR often failed recognising single digits. As mentioned above, the detection is still not perfect and I'll be working on improving it.

- UPDATE: EasyOCR is now used for VCT matches

3. **Moviepy is slow**

- From testing, moviepy takes rather long (about 5 minutes, not more than 10 minutes) to render a ~1 min video.
- However, I haven't found a way to fix this. Perhaps [using the ffmpeg_tools directly](https://stackoverflow.com/questions/56413813/concat-videos-too-slow-using-python-moviepy) in the moviepy library may work better (will try in the future)

### Future updates

- More customisation options in config.ini
- ~~Integrating the original [VTOK 1.0](https://github.com/Techie-Ernie/vtok) into this new version - will need to update moviepy as well since VTOK 1.0 used moviepy 1.x, which has been updated to 2.x + support for VCT matches (however, [vlr.gg](https://vlr.gg) and [valorant.op.gg](https://valorant.op.gg) don't currently provide the stats I need, and [rib.gg](https://rib.gg) has shut down on 1st Dec 2024)~~ **UPDATE: Switched to [vlr.gg](https://vlr.gg) scraper (no Selenium required). vlr.gg does not expose per-round kill counts, so all elimination rounds from maps with 4K/5K players are used as highlight candidates - Added June 2026**
- Better OCR accuracy: WIP
- Support for Twitch vods on top of YouTube
- ~~Finding the match stats on valorant.op.gg directly from the YouTube video~~ **Added on 5/12/24**
