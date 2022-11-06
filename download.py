from __future__ import unicode_literals
import yt_dlp

def downloadURL(url, destination):
    #blocks until complete
    ydl_opts = {
        'outtmpl':destination
        }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
