from faster_whisper import WhisperModel
import os


def _format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


# SecondaryColour (&H0000FFFF = yellow) is the pre-karaoke colour — each word
# sweeps from yellow to white (\kf) as it's spoken, giving a TikTok-style highlight.
_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,55,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,10,10,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

_BASE_PROMPT = (
    "Valorant, VCT, spike, Phantom, Vandal, Operator, Sheriff, Spectre, Odin, Ares, "
    "Jett, Reyna, Phoenix, Neon, Raze, Yoru, Iso, Sage, Cypher, Killjoy, Chamber, "
    "Deadlock, Brimstone, Omen, Viper, Astra, Harbor, Sova, Skye, Breach, Fade, Gekko, "
    "eco, full buy, force buy, half buy, clutch, ace, 4K, 5K, plant, defuse, retake, "
    "rotate, smoke, flash, molly, dart, recon, ultimate, ult, Ascent, Bind, Haven, "
    "Split, Icebox, Breeze, Fracture, Pearl, Lotus, Sunset, Abyss"
)

WORDS_PER_CHUNK = 3


def _flush_chunk(f, chunk):
    """Write one karaoke dialogue line from a list of (text, start, end) tuples."""
    if not chunk:
        return
    line_start = chunk[0][1]
    line_end = chunk[-1][2]
    parts = []
    for j, (text, ws, we) in enumerate(chunk):
        # Duration covers the gap to the next word so timing stays gapless.
        if j + 1 < len(chunk):
            cs = max(1, int((chunk[j + 1][1] - ws) * 100))
        else:
            cs = max(1, int((we - ws) * 100))
        parts.append(f"{{\\kf{cs}}}{text}")
    f.write(
        f"Dialogue: 0,{_format_ass_time(line_start)},"
        f"{_format_ass_time(line_end)},Default,,0,0,0,," + " ".join(parts) + "\n"
    )


def transcribe_audio(input_file, words, gpu, vocabulary=None):
    model_size = "large-v3"

    if gpu:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
    else:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    ass_filename = os.path.splitext(input_file)[0] + ".ass"

    if words:
        match_terms = ", ".join(vocabulary) if vocabulary else ""
        prompt = f"{match_terms}, {_BASE_PROMPT}" if match_terms else _BASE_PROMPT
        segments, info = model.transcribe(
            input_file,
            word_timestamps=True,
            initial_prompt=prompt,
            # hotwords boosts these tokens in beam search — stronger than initial_prompt alone
            hotwords=match_terms if match_terms else None,
        )
        print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

        with open(ass_filename, "w", encoding="utf-8") as f:
            f.write(_ASS_HEADER)
            chunk = []
            for segment in segments:
                for word in segment.words:
                    text = word.word.strip()
                    if not text:
                        continue
                    chunk.append((text, word.start, word.end))
                    if len(chunk) >= WORDS_PER_CHUNK:
                        _flush_chunk(f, chunk)
                        chunk = []
            _flush_chunk(f, chunk)
    else:
        segments, _ = model.transcribe(input_file)
        with open(ass_filename, "w", encoding="utf-8") as f:
            f.write(_ASS_HEADER)
            for segment in segments:
                f.write(
                    f"Dialogue: 0,{_format_ass_time(segment.start)},"
                    f"{_format_ass_time(segment.end)},Default,,0,0,0,,{segment.text.lstrip()}\n"
                )
    return ass_filename
