import download
from moviepy.editor import VideoFileClip, CompositeAudioClip, clips_array, ColorClip, concatenate_videoclips
from moviepy.audio.fx.audio_normalize import audio_normalize
from math import sqrt, ceil
import numpy
import ffmpeg

def vidArrayFromFilenames(filenames):
    # moviepy version
    a = []
    for filename in filenames:
        a.append(VideoFileClip(filename))
    return a


def vidDictionaryFromFilenames(filenames):
    # moviepy version
    d = {}
    for filename in filenames:
        d[filename] = VideoFileClip(filename)

    return d


def formatTime(seconds):
    #formats time for display, used in debugging
    assert (seconds >= 0)
    s = str(int(seconds % 60))
    return str(int(seconds // 60)) + ":" + ("0" * (2 - len(s))) + s


placeholderVideo = ColorClip((20, 20), (0, 0, 0), duration=1 / 60)

def make_subclip(filename, startInsideClip, endInsideClip, destination, width=None, fps=None):
    #cuts a cubclip out from a source clip
    clip = VideoFileClip(filename)
    clip = clip.subclip(startInsideClip, endInsideClip)
    if width != None:
        clip = clip.resize(width=width)
    if fps == None:
        clip.write_videofile(destination)
    else:
        clip.write_videofile(destination, fps=fps)


def viewTimeline(clips):
    # renders all the clips side-by-side
    clipCountWidth = int(ceil(sqrt(len(clips))))
    clipCountHeight = ceil(len(clips) / clipCountWidth)
    print("width:", clipCountWidth, "height:", clipCountHeight)
    reordered_array = []
    for i in range(clipCountHeight):
        newRow = []
        for j in range(clipCountWidth):
            index = (clipCountWidth * i) + j
            if index < len(clips):
                newRow.append(clips[index])
            else:
                newRow.append(placeholderVideo)
        if len(newRow) > 0:
            reordered_array.append(newRow)
    combined = clips_array(reordered_array)
    return combined


def renderVideoFromCutList(filenamesToClips, cutList, startTimes, maxFade=5):
    # takes the cutlist from the core optimizer and produces a VideoClip for the final render

    # initialise audio reference points
    midpoints = {}
    midlefts = {}
    midrights = {}

    midpoints[0] = cutList[0].timeAfter / 2
    midlefts[0] = 0
    midrights[0] = max(midpoints[0], cutList[0].timeAfter - maxFade, startTimes[cutList[0].filenameAfter])
    midrights[-1] = -1 / 60  # to avoid singularities when using lerp

    # populate audio reference points
    for i in range(1, len(cutList)):
        # set midpoints, midlefts and midrights for the ith shot in the video
        midpoints[i] = (cutList[i - 1].timeAfter + cutList[i].timeAfter) / 2
        midlefts[i] = min(midpoints[i], cutList[i - 1].timeAfter + maxFade,
                          filenamesToClips[cutList[i - 1].filenameBefore].duration + startTimes[
                              cutList[i - 1].filenameBefore])
        midrights[i] = max(midpoints[i], cutList[i].timeAfter - maxFade, startTimes[cutList[i].filenameAfter])

    # add audio reference points for the last shot in the video
    midpoints[len(cutList)] = (cutList[-1].timeAfter + (
                startTimes[cutList[-1].filenameAfter] + filenamesToClips[cutList[-1].filenameAfter].duration)) / 2
    midlefts[len(cutList)] = min(midpoints[len(cutList)], cutList[-1].timeAfter + maxFade,
                                 filenamesToClips[cutList[-1].filenameBefore].duration + startTimes[
                                     cutList[-1].filenameBefore])
    midrights[len(cutList)] = startTimes[cutList[-1].filenameAfter] + filenamesToClips[
        cutList[-1].filenameAfter].duration
    midlefts[len(cutList) + 1] = midrights[len(cutList)] + (1 / 60)

    # initialize video segments variables
    currentTime = 0
    shots = []
    shotFilenames = []
    shotIndexedStart = {}
    shotIndexedEnd = {}
    i = 0

    # add all video shots
    for cut in cutList:
        shotFilenames.append(cut.filenameBefore)
        sourceClip = filenamesToClips[cut.filenameBefore]

        # cuts takes place on cut.timeAfter because the frame cut to may be the first frame in the video
        # whereas the frame beginning at cut.timeBefore is guaranteed to continue at least until cut.timeAfter
        endTime = cut.timeAfter
        shots.append(
            sourceClip.subclip(currentTime - startTimes[cut.filenameBefore], endTime - startTimes[cut.filenameBefore]))
        shots[-1] = shots[-1].crossfadein(2.0)
        shotIndexedStart[i] = currentTime - startTimes[cut.filenameBefore]
        shotIndexedEnd[i] = endTime - startTimes[cut.filenameBefore]
        currentTime = endTime
        i += 1

    # add the last clip
    lastClip = filenamesToClips[cutList[-1].filenameAfter]
    shotFilenames.append(cutList[-1].filenameAfter)
    shotIndexedStart[i] = currentTime - startTimes[cutList[-1].filenameAfter]
    shotIndexedEnd[i] = lastClip.duration
    shots.append(lastClip.subclip(currentTime - startTimes[cutList[-1].filenameAfter], lastClip.duration))

    # mix audio for each shot in preparation for composite
    audioShots = []
    for i in range(len(cutList) + 1):
        filename = shotFilenames[i]
        print("normalising audio")
        audioClipCopy = filenamesToClips[filename].set_start(startTimes[filename]).fx(audio_normalize)

        # each audio clip starts from zero outside the clip, fades up to 1 at a point inside the clip,
        # and then at some point fades down from 1 to 0 across the next cut
        firstZeroPoint = midrights[i - 1] - startTimes[filename]
        firstOnePoint = midlefts[i] - startTimes[filename]
        secondOnePoint = midrights[i] - startTimes[filename]
        secondZeroPoint = midlefts[i + 1] - startTimes[filename]

        try:
            # assert the times of the points are in the correct order - something's probably gone wrong if they aren't
            assert (firstZeroPoint <= firstOnePoint <= secondOnePoint <= secondZeroPoint)
        except AssertionError:
            print("assertionerror thrown on i=", i)
            print("firstZeroPoint", firstZeroPoint, "firstOnePoint", firstOnePoint, "secondOnePoint", secondOnePoint,
                  "secondZeroPoint", secondZeroPoint)
            raise

        # function applied to the audio to apply the fades
        # i=i is used to capture the specific value of i on this loop iteration
        def fun(gf, t, i=i, firstZeroPoint=firstZeroPoint, firstOnePoint=firstOnePoint, secondOnePoint=secondOnePoint,
                secondZeroPoint=secondZeroPoint):
            # make sure the t is actually the audio times
            # this is run once on the video frames
            # so it needs to detect this and return early
            if type(t) == int:
                return gf(t)
            elif len(gf(t).shape) == 3:
                return gf(t)

            volume_multiplier = numpy.interp(t, [firstZeroPoint, firstOnePoint, secondOnePoint, secondZeroPoint],
                                             [0, 1, 1, 0])
            original = gf(t)
            return original * volume_multiplier[:, None]

        # function application
        audioClipCopy = audioClipCopy.fl(fun, apply_to='audio')
        audioShots.append(audioClipCopy.audio)

    compositeAudio = CompositeAudioClip(audioShots)

    # finally, concatenate the shots and add the audio
    combined = concatenate_videoclips(shots)
    combined.audio = compositeAudio
    return combined
