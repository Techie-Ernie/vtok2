from faster_whisper import WhisperModel
import os
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing import CompositeVideoClip
from moviepy.video.io.ffmpeg_writer import ffmpeg_write_video


def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    milliseconds = (seconds - int(seconds)) * 1000
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"  # This is the format for srt file


def transcribe_audio(input_file, words, gpu):
    model_size = "large-v3"

    if gpu:  # Run on GPU with FP16
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        # or run on GPU with INT8
        # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
    else:
        # or run on CPU with INT8
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
    # Initial prompt helps the model recognise the nouns unique to the situation (e.g. valorant)
    if words:
        segments, info = model.transcribe(
            input_file,
            word_timestamps=True,
            initial_prompt="Paper Rex, Evil Geniuses, davai, mindfreak, f0rsakeN, , jinggg, jawgemo, Boostio, Demon1, Ethan, Com, Ascent, Bind, Haven, Split, Icebox, Breeze, Fracture, Pearl, Lotus, Spike, Eco, Full Buy, Half Buy, Operator, Phantom, Vandal, Sheriff, Ghost, Spectre, Ares, Odin, Ultimate, Clutch, Ace, Rotate, Retake, Push, Defuse, Plant, Smurf, Peek, Flash, Molly, Smoke, Dart, Recon, Ult Orb, Spike Rush, Competitive, Unrated, Deathmatch, Spike Plant, Spike Defuse, Omen, Jett, Phoenix, Reyna, Sage, Sova, Cypher, Killjoy, Brimstone, Viper, Astra, Skye, Yoru, Breach, Raze, Chamber, Neon, Fade, Harbor, Gekko, Deadlock, Iso, Team Deathmatch, Premier Mode, Ranked, Radiant, Immortal, Diamond, Platinum, Gold, Silver, Bronze, Iron, Clutch Minister, IGL, Lurker, Entry Fragger, Controller, Sentinel, Duelist, Initiator, Crosshair, Spray Control, Headshot, Body Shot, Footwork, Utility, Economy, Anti-Eco, Force Buy, Operator Play, Wallbang, One-Tap, Trade Kill, Post-Plant, Pre-Plant, Default, Execute, Fake, Retake, Rotate, Lurking, Peekers Advantage, Map Control, Site Execute, Site Hold, Site Take, Spike Carrier, Spike Runner, Team Synergy, Comms, Callouts, Flank, Bait, Trade, Mid Control, Split Push, Default Play, Aggro Play, Passive Play, Utility Usage, Ult Economy, Teamfight, Post-Plant, Map Pick, Map",
        )

        print(
            "Detected language '%s' with probability %f"
            % (info.language, info.language_probability)
        )
        srt_filename = os.path.splitext(input_file)[0] + ".srt"

        with open(srt_filename, "w", encoding="utf-8") as srt_file:
            count = 1
            for segment in segments:
                for word in segment.words:
                    start_time = format_time(word.start)
                    end_time = format_time(word.end)
                    line = f"{count}\n{start_time} --> {end_time}\n{word.word.lstrip()}\n\n"
                    count += 1
                    srt_file.write(line)
    else:
        segments, info = model.transcribe(input_file)
        srt_filename = os.path.splitext(input_file)[0] + ".srt"
        with open(srt_filename, "w", encoding="utf-8") as srt_file:
            for segment in segments:
                start_time = format_time(segment.start)
                end_time = format_time(segment.end)
                line = f"{segment.id + 1}\n{start_time} --> {end_time}\n{segment.text.lstrip()}\n\n"
                srt_file.write(line)
    return srt_filename


def add_subtitles(
    audio,
    video,
    srt,
    output_path,
    text_font_size=100,
    text_colour="white",
    text_stroke_colour="black",
    vertical_align="center",
    text_font="Roboto-Bold.ttf",
):
    vid = VideoFileClip(video)
    generator = lambda text: TextClip(
        text=text,
        font=text_font,
        font_size=text_font_size,
        color=text_colour,
        stroke_width=10,
        margin=(None, 700),
        stroke_color=text_stroke_colour,
        vertical_align=vertical_align,
        size=vid.size,
    )
    sub = SubtitlesClip(srt, make_textclip=generator)
    final = CompositeVideoClip.CompositeVideoClip([vid, sub], size=vid.size)
    ffmpeg_write_video(final, output_path, fps=vid.fps, audiofile=audio)
