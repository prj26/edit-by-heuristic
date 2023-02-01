import download
from moviepy.editor import VideoFileClip, CompositeAudioClip, clips_array, ColorClip, concatenate_videoclips
from math import sqrt, ceil
import numpy
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

def vidDictionaryFromFilenames(filenames):
    #moviepy version
    d = {}
    for filename in filenames:
        d[filename] = VideoFileClip(filename)
    return d

def formatTime(seconds):
    assert(seconds >= 0)
    s = str(int(seconds % 60))
    return str(int(seconds // 60)) + ":" + ("0" * (2 - len(s))) + s

placeholderVideo = ColorClip((1,1), (0,0,0), duration=1 / 60)

def viewTimeline(clips):
    #moviepy version
    clipCountWidth = int(ceil(sqrt(len(clips))))
    clipCountHeight = ceil(len(clips)/clipCountWidth)
    print("width:",clipCountWidth,"height:",clipCountHeight)
    reordered_array = []
    for i in range(clipCountHeight):
        newRow = []
        for j in range(clipCountWidth):
            index = (clipCountWidth*i)+j
            if index < len(clips):
                newRow.append(clips[index])
            else:
                newRow.append(placeholderVideo)
        if len(newRow) > 0:
            reordered_array.append(newRow)
    combined = clips_array(reordered_array)
    return combined

def renderVideoFromCutList(filenamesToClips, cutList, startTimes, maxFade=5):
    currentTime = 0
    shots = []
    print("rendering video from cutList")
    midpoints = {}
    midlefts = {}
    midrights = {}
    midpoints[0] = cutList[0].timeAfter/2
    midlefts[0] = 0
    midrights[0] = max(midpoints[0], cutList[0].timeAfter - maxFade, startTimes[cutList[0].filenameAfter])
    midrights[-1] = -1/60#to avoid singularities when using lerp
    for i in range(1,len(cutList)):
        #set midpoints, midlefts and midrights for the ith shot in the video
        midpoints[i] = (cutList[i-1].timeAfter + cutList[i].timeAfter) / 2
        midlefts[i] = min(midpoints[i], cutList[i-1].timeAfter + maxFade, filenamesToClips[cutList[i-1].filenameBefore].duration + startTimes[cutList[i-1].filenameBefore])
        midrights[i] = max(midpoints[i], cutList[i].timeAfter - maxFade, startTimes[cutList[i].filenameAfter])
    midpoints[len(cutList)] = (cutList[-1].timeAfter + (startTimes[cutList[-1].filenameAfter] + filenamesToClips[cutList[-1].filenameAfter].duration))/2
    midlefts[len(cutList)] = min(midpoints[len(cutList)], cutList[-1].timeAfter + maxFade, filenamesToClips[cutList[-1].filenameBefore].duration + startTimes[cutList[-1].filenameBefore])
    midrights[len(cutList)] = startTimes[cutList[-1].filenameAfter]+filenamesToClips[cutList[-1].filenameAfter].duration
    midlefts[len(cutList)+1] = midrights[len(cutList)]+(1/60)
    shotFilenames = []
    shotIndexedStart = {}
    shotIndexedEnd = {}
    i = 0
    for cut in cutList:
        shotFilenames.append(cut.filenameBefore)
        sourceClip = filenamesToClips[cut.filenameBefore]
        endTime = cut.timeAfter
        shots.append(sourceClip.subclip(currentTime - startTimes[cut.filenameBefore], endTime - startTimes[cut.filenameBefore]))
        shots[-1] = shots[-1].crossfadein(2.0)
        print("cutting from",cut.filenameBefore,"to",cut.filenameAfter,"at",formatTime(endTime))
        print("indexed inside",cut.filenameBefore,"the timings are",currentTime - startTimes[cut.filenameBefore], endTime - startTimes[cut.filenameBefore])
        shotIndexedStart[i] = currentTime - startTimes[cut.filenameBefore]
        shotIndexedEnd[i] = endTime - startTimes[cut.filenameBefore]
        print("the duration of "+cut.filenameBefore+" is",filenamesToClips[cut.filenameBefore])
        currentTime = endTime
        i += 1
    lastClip = filenamesToClips[cutList[-1].filenameAfter]
    shotFilenames.append(cutList[-1].filenameAfter)
    print("ending with a shot of",cutList[-1].filenameAfter,"with indexed times",currentTime - startTimes[cutList[-1].filenameAfter], lastClip.duration)
    shotIndexedStart[i] = currentTime - startTimes[cutList[-1].filenameAfter]
    shotIndexedEnd[i] = lastClip.duration
    print("the duration is",lastClip.duration)
    shots.append(lastClip.subclip(currentTime - startTimes[cutList[-1].filenameAfter], lastClip.duration))

    print("ending with a shot of",filenamesToClips[cutList[-1].filenameAfter]," from the video indexed start at",currentTime - startTimes[cutList[-1].filenameAfter],"to",lastClip.duration)
    print("this accounts for",formatTime(lastClip.duration - (currentTime - startTimes[cutList[-1].filenameAfter])),"seconds, and should bring the total video up to",formatTime(startTimes[cutList[-1].filenameAfter]+lastClip.duration))

    #mix audio for each shot in preparation for composite
    audioShots = []
    for i in range(len(cutList)+1):
        filename = shotFilenames[i]
        audioClipCopy = filenamesToClips[filename].set_start(startTimes[filename])
        #audioClipCopy = audioClipCopy.subclip(shotIndexedStart[i],shotIndexedEnd[i])

        firstZeroPoint = midrights[i-1]
        firstOnePoint = midlefts[i]
        secondOnePoint = midrights[i]
        secondZeroPoint = midlefts[i+1]
        print("printing times for video",shotFilenames[i],"in shot",i)
        print("firstZeroPoint",firstZeroPoint,"firstOnePoint",firstOnePoint,"secondOnePoint",secondOnePoint,"secondZeroPoint",secondZeroPoint)
        print("formatted:")

        try:
            assert(firstZeroPoint <= firstOnePoint <= secondOnePoint <= secondZeroPoint)
        except AssertionError:
            print("assertionerror thrown on i=",i)
            print("firstZeroPoint",firstZeroPoint,"firstOnePoint",firstOnePoint,"secondOnePoint",secondOnePoint,"secondZeroPoint",secondZeroPoint)
            raise
        def fun(gf, t, i=i, firstZeroPoint=firstZeroPoint, firstOnePoint=firstOnePoint, secondOnePoint=secondOnePoint, secondZeroPoint=secondZeroPoint):


            if type(t) == int:
                return gf(t)
            elif len(gf(t).shape) == 3:
                return gf(t)

            #print("t:",t)
            #print("middle t:",t[t.size//2])
            volume_multiplier = numpy.interp(t, [firstZeroPoint, firstOnePoint, secondOnePoint, secondZeroPoint], [0, 1, 1, 0])
            #volume_multiplier = numpy.ones(t.shape)
            frame = gf(t)
            #print("volume:",volume_multiplier)
            #print("middle volume:",volume_multiplier[volume_multiplier.size//2])
            #print("points for i=",i,":",[firstZeroPoint, firstOnePoint, secondOnePoint, secondZeroPoint])
            #return frame
            return frame * volume_multiplier[:, None]

        audioClipCopy = audioClipCopy.fl(fun, apply_to='audio')
        audioShots.append(audioClipCopy.audio)

    compositeAudio = CompositeAudioClip(audioShots)

    combined = concatenate_videoclips(shots)
    combined.audio = compositeAudio
    print("combined duration:",combined.duration,"("+formatTime(combined.duration)+")")
    return combined
