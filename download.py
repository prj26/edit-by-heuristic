from __future__ import unicode_literals
import yt_dlp


def downloadURL(url, destination, progressHook=lambda x:x):
    # a wrapper over yt-dlp, using the recommended implementation
    # blocks until complete
    ydl_opts = {
        'outtmpl': destination,
        'format': 'best[ext=mp4]',
        'progress_hooks': [progressHook]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
