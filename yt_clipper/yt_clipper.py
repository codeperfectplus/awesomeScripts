#! /usr/bin/env python3
#
# ---------------------------------------------------------------
# Easily make audio/video/gif clips from YouTube URLs with ffmpeg
#
# (C) 2020-2021 Ezequiel Pássaro
# Released under MIT License
#
# github: github.com/epassaro
# email: epassaro15@gmail.com
# ---------------------------------------------------------------
#

import re
import argparse
import subprocess


def find_url(string):
    """Finds an arbitrary number of URLs in a string and returns them in a list.
    Taken from: https://www.geeksforgeeks.org/python-check-url-string/"""
    regex = (
        r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s"
        r"()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s("
        r")<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    )
    url = re.findall(regex, string)

    return [x[0] for x in url]


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="easily make audio/video/gif clips from YouTube URLs with ffmpeg"
    )
    parser.add_argument("url", help="video url")
    parser.add_argument("start", help="HH:MM:SS.ms")
    parser.add_argument("end", help="HH:MM:SS.ms")
    parser.add_argument(
        "-d",
        "--device",
        help="device for VA-API hardware acceleration (experimental), for example: '/dev/dri/render128D'",
        type=str,
        default="",
    )
    parser.add_argument(
        "-s", "--scale", help="scale image vertically (in px)", type=int, default=-2
    )
    parser.add_argument("-a", "--audio-only", action="store_true", dest="audio_only")
    parser.add_argument("-g", "--gif", action="store_true")
    parser.add_argument("-f", "--fps", help="gif fps", type=int, default=12)
    parser.add_argument("-o", "--output")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    # Get video ID to use as default file name
    get_id = subprocess.Popen(
        ["youtube-dl", "--get-id", args.url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    video_id = None
    while not video_id:  # Sometimes `get_id` returns nothing
        out, err = get_id.communicate()
        get_id.wait()
        video_id = out.strip()  # Remove newlines

    # Get video and audio URLs
    get_url = subprocess.Popen(
        ["youtube-dl", "-g", args.url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    out, err = get_url.communicate()
    get_url.wait()
    video_url, audio_url = find_url(out)

    # Set variables for CPU or GPU processing (video only)
    if not args.device:
        codec = "libx264"
        vaapi = ""
        scale = f"scale={args.scale}:-2:flags=lanczos"

    else:
        codec = "h264_vaapi"
        vaapi = (
            f"-hwaccel vaapi -hwaccel_output_format vaapi -hwaccel_device {args.device}"
        )
        scale = f"scale_vaapi={args.scale}:-2"

    # Define ffmpeg commands
    ffmpeg_cmd = f"ffmpeg {vaapi} -ss {args.start} -to {args.end} -i {video_url} -ss {args.start}\
                    -to {args.end} -i {audio_url} -map 0:v -map 1:a -c:v {codec} -c:a aac\
                        -vf {scale} -y {video_id}.mp4"

    if args.audio_only:
        ffmpeg_cmd = f"ffmpeg -ss {args.start} -to {args.end} -i {audio_url} -c:a aac -y\
                        {video_id}.aac"

    if args.gif:
        ffmpeg_cmd = (
            f"ffmpeg -ss {args.start} -to {args.end} -i {video_url}"
            f" -filter_complex [0:v]fps={args.fps},scale={args.scale}:-2:flags=lanczos,"
            "split[a][b];[a]palettegen[p];[b][p]paletteuse"
            f" -y {video_id}.gif"
        )

    # Split command in a list to use later with subprocess.Popen
    ffmpeg_args = ffmpeg_cmd.split()

    if args.output:
        ffmpeg_args[-1] = args.output

    if args.quiet:
        ffmpeg_args = ffmpeg_args + ["-v", "fatal"]

    # Run ffmpeg
    make_clip = subprocess.Popen(ffmpeg_args)
    make_clip.wait()
