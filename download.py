from __future__ import unicode_literals
import yt_dlp


def downloadURL(url, destination):
    # blocks until complete
    ydl_opts = {
        'outtmpl': destination,
        'format': 'best[ext=mp4]'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
