import download
from moviepy.editor import VideoFileClip, clips_array
from math import sqrt
import ffmpeg

"""
def vidArrayFromFilenames(filenames):
    #ffmpeg-python version
    a = []
    for filename in filenames:
        a.append(ffmpeg.input(filename))
    return a

def viewComposed(in_files):
    in1 = in_files[0]
    in2 = in_files[0]
    v1 = in1.video.hflip()
    a1 = in1.audio
    v2 = in2.video.filter('reverse').filter('hue', s=0)
    a2 = in2.audio.filter('areverse').filter('aphaser')
    joined = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1).node
    v3 = joined[0]
    a3 = joined[1].filter('volume', 0.8)
    out = ffmpeg.output(v3, a3, 'out.mp4')
    out.run()
"""

def vidArrayFromFilenames(filenames):
    #moviepy version
    a = []
    for filename in filenames:
        a.append(VideoFileClip(filename))
    return a

def viewTimeline(clips):
    #moviepy version
    clipCountWidth = int(sqrt(len(clips))+1)
    clipCountHeight = len(clips)//clipCountWidth
    reordered_array = []
    for i in range(clipCountHeight):
        newRow = []
        for j in range(clipCountWidth):
            index = (clipCountWidth*i)+j
            if index < len(clips):
                newRow.append(clips[index])
        if len(newRow) > 0:
            reordered_array.append(newRow)
    combined = clips_array(reordered_array)
    return combined
