from genericpath import exists
import pafy
import os
from pydub import AudioSegment
import time
import datetime

from telegram.ext.dispatcher import run_async


def download_audio(video_id, video_url):
    os.makedirs("./dist", exist_ok=1)
    if not video_id:
        return {"status": False, "error": "Video id not specified"}

    try:
        video = pafy.new(str(video_url))
    except ValueError as e:
        print(e)
        return {"status": False, "error": "Invalid video id specified"}

    path = get_song(video.title)

    if path:
        return {
            "status": True,
            "path": path,
            "duration": get_duration(video.duration),
            "title": video.title,
        }

    streams = video.audiostreams
    if len(streams) > 0:
        video.getbestaudio().download(filepath="./dist", quiet=False)
        filename = get_filename(video.title)
        convert_to_mp3(filename, video.title)
        os.remove(filename)
        file_path = "./dist/%s.mp3" % video.title
        return {
            "status": True,
            "path": file_path,
            "duration": get_duration(video.duration),
            "title": video.title,
        }

    return {"status": False, "error": "No audio streams found"}


def get_song(title):
    path = "./dist/" + title + ".mp3"
    if os.path.exists(path):
        return path

    return None


def convert_to_mp3(path, title):
    AudioSegment.from_file(path).export("./dist/" + title + ".mp3", format="mp3")


def get_filename(title):
    for file_ in os.listdir("./dist"):
        if not file_.startswith(title):
            continue
        return os.path.join("./dist", file_)


def get_duration(time_str):
    x = time.strptime(time_str, "%H:%M:%S")
    return datetime.timedelta(
        hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec
    ).total_seconds()
