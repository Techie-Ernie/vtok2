import subprocess


_BUY_PHASE = 30   # seconds to skip past the buy phase so the clip starts at round gameplay
_ROUND_MAX = 130  # fallback clip length from gameplay start (buy 30s + round 100s + buffer)


def convert_rounds(score_dict):
    return dict(enumerate(score_dict.values(), start=1))


def extract_clip(vod_path, round_dict, highlights_dict):
    print(f"Round dict: {round_dict}")
    video_count = 0
    for i, rnd in enumerate(highlights_dict.keys()):
        if rnd not in round_dict:
            print(f"Round {rnd} not in round_dict — skipping")
            continue
        start = round_dict[rnd] + _BUY_PHASE
        end = round_dict.get(rnd + 1, start + _ROUND_MAX)
        output = f"video{i}.mp4"
        try:
            # Stream copy: seeks to nearest keyframe, copies without re-encoding. Near-instant.
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(start), "-to", str(end),
                 "-i", vod_path, "-c", "copy", output],
                check=True, capture_output=True,
            )
            print(f"Clipped round {rnd}: {start:.1f}s – {end:.1f}s → {output}")
            video_count += 1
        except subprocess.CalledProcessError as e:
            print(f"Error clipping round {rnd}: {e.stderr.decode()[-400:]}")
    return video_count
