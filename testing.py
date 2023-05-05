from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

import download
import geotagsearch
import videoedit
import audiosync
import coreoptimizer

import json
import os
import datetime
import random

def filterWembley(searchq):
    return geotagsearch.urlsFromSearchWithFilter(lambda x: geotagsearch.filterByVideoTitle(x, searchq), searchq,
                                                 "51.556027024933016, -0.2796255654208833", "0.75km", 120)


def printjson(o):
    print(json.dumps(o, sort_keys=True, indent=4))


def printTitles(response):
    for v in response["items"]:
        print(v["snippet"]["title"])
        print("https://www.youtube.com/watch?v=" + v["id"]["videoId"])


def downloadUrls(urls):
    for i in range(len(urls)):
        download.downloadURL(urls[i], "C:\\Users\\User\\Music\\folder\\vid" + str(i) + '.%(ext)s')


def getFrame(filename):
    # partially adapted from a stackoverflow answer
    # https://stackoverflow.com/questions/42163058/how-to-turn-a-video-into-numpy-array
    import cv2
    cap = cv2.VideoCapture(filename)
    frameCount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fc = 0
    ret = True

    while (fc < frameCount and ret):
        ret, a = cap.read()
        return a

    cap.release()



pretend1 = 'C:\\Users\\User\\Documents\\PartIIProject\\projectvideoeditor\\thepretender-CIskdB33wnw.mp4'
pretend2 = 'C:\\Users\\User\\Documents\\PartIIProject\\projectvideoeditor\\thepretender-o6xQj-a_aqI.mp4'
pretend3 = 'C:\\Users\\User\\Documents\\PartIIProject\\projectvideoeditor\\thepretender-yvb4RE2FKeY.mp4'
pretenders = ["C:\\Users\\User\\Music\\folder\\vid"+str(i)+".webm" for i in range(6)]
tsfh = "C:\\Users\\User\\Music\\two_steps_from_hell.mp3"
tsfh_delayed = "C:\\Users\\User\\Music\\two_steps_from_hell_delayed.mp3"
output = "C:\\Users\\User\\Music\\output2.mp4"
test_output = "C:\\Users\\User\\Music\\test_output.mp4"
audio_output = "C:\\Users\\User\\Music\\audio_output.mp3"
def render_synced_array():
    filenames = pretenders
    clips = videoedit.vidArrayFromFilenames(filenames)
    start_times = audiosync.constructTimeline(filenames)
    print("start_times:",start_times)
    for i in range(len(clips)):
        clips[i] = clips[i].set_start(start_times[filenames[i]])
    combined = videoedit.viewTimeline(clips)
    combined.resize(width=480).write_videofile(output, fps=1)

def optimizeTest():
    filenames = pretenders
    clipsDict = videoedit.vidDictionaryFromFilenames(filenames)
    #start_times = audiosync.constructTimeline(filenames)
    start_times = {'C:\\Users\\User\\Music\\folder\\vid3.webm': 0, 'C:\\Users\\User\\Music\\folder\\vid2.webm': 64.04135416666666, 'C:\\Users\\User\\Music\\folder\\vid5.webm': 27.841437499999998, 'C:\\Users\\User\\Music\\folder\\vid1.webm': 84.06745833333333, 'C:\\Users\\User\\Music\\folder\\vid4.webm': 333.6718333333333, 'C:\\Users\\User\\Music\\folder\\vid0.webm': 153.67320833333332}
    print("start_times")
    print(", ".join([name + ":" + videoedit.formatTime(start_times[name]) for name in filenames]))
    optimizer = coreoptimizer.FrameTimelinesOptimizer(filenames, start_times)
    result = optimizer.optimizeWithFixedCosts(coreoptimizer.tenegrad_sobel_heuristic, 1, 360)
    print(result)
    print(result.cutHistory)
    print("result's filename's start time is",start_times[result.filename])
    print("result's filename's video's duration is",clipsDict[result.filename].duration)
    #from coreoptimizer import Cut
    #artificial_history = [Cut(24.0,filenames[3],33.85175421196406,filenames[5]), Cut(226.181888994814, filenames[5], 228.13097234274753, filenames[2]),Cut(341.7314772338804, filenames[2], 345.6838333333333, filenames[4]), Cut(369.7078333333333, filenames[4], 373.2871730369729, filenames[2]), Cut(417.46514716130235,filenames[2], 420.0, filenames[3]),Cut(420.0, filenames[3], 424.52234048962737, filenames[5])]
    s = start_times[result.filename] + clipsDict[result.filename].duration
    print("the sum of these is",s,"("+videoedit.formatTime(s)+")")
    combined = videoedit.renderVideoFromCutList(clipsDict, result.cutHistory, start_times)
    combined.resize(width=480).write_videofile(output, fps=30)
    #clipsDict[filenames[3]].write_audiofile(audio_output,fps=30)

def test_audio_transition():
    clip1 = videoedit.VideoFileClip(pretend1).subclip(0,20)
    clip2 = videoedit.VideoFileClip(pretend2).subclip(0,20)
    clip2 = clip2.set_start(clip1.duration)
    #combined = videoedit.concatenate_videoclips([clip1,clip2])
    combined = clip1
    import moviepy.editor
    import moviepy
    # using stackoverflow https://stackoverflow.com/questions/55032551/moviepy-add-audio-to-a-video
    fadeout = moviepy.audio.fx.all.audio_fadeout(clip1, 5)
    def fun(gf, t):
        if type(t) == int:
            return gf(t)
        elif len(gf(t).shape) == 3:
            return gf(t)
        frame = gf(t)
        return frame * t[:, None]

    clip1 = clip1.fl(fun, apply_to='audio')
    print("all audio options:",dir(moviepy.audio.fx.all))
    #clip1.audio = fadeout.audio
    clip1.resize(width=480).write_videofile(test_output, fps=30)




def make_subclips(filenames, start_times, duration, destinationFolder):
    startTime = max([start_times[i] for i in filenames])
    endTime = min(min([start_times[i]+audiosync.getVideoDuration(i) for i in filenames]), startTime+duration)
    index = 0
    for filename in filenames:
        print("calling make_subclip with times",startTime - start_times[filename], endTime - start_times[filename])
        videoedit.make_subclip(filename, startTime - start_times[filename], endTime - start_times[filename], destinationFolder+"\\extract"+str(index)+".mp4", 480, 30)
        index += 1

def make_subclip_folder(filenames, start_times, duration, destinationFolderLocation, destinationFolderName):
    newFolderPath = destinationFolderLocation+"\\"+destinationFolderName
    os.mkdir(newFolderPath)
    print("make_subclip_folder called with duration=",duration)
    make_subclips(filenames, start_times, duration, newFolderPath)

def timeOptimizer(filenames):
    start_times = {i:0 for i in filenames}
    heuristic = lambda frame,duration:(coreoptimizer.tenegrad_sobel_heuristic(frame, duration) * coreoptimizer.brightheuristic(frame, duration))

    #start timer
    before = datetime.datetime.now()

    optimizer = coreoptimizer.FrameTimelinesOptimizer(filenames, start_times)
    result = optimizer.optimizeWithFixedCosts(heuristic, 1, 1)

    #finish timer
    after = datetime.datetime.now()

    difference = after - before
    return difference.total_seconds()

def timeOptimizerFromFolder(folderPath):
    filenames = [folderPath+"\\extract"+str(i)+".mp4" for i in range(5)]
    return timeOptimizer(filenames)

def timeOptimizerBatch(folderPath, testNumbers):
    results = []
    for testNumber in testNumbers:
        results.append(timeOptimizerFromFolder(folderPath+"\\test"+str(testNumber)))
    return results

def benchmark():
    benchmarkPath = "C:\\Users\\User\\Documents\\PartIIProject\\projectvideoeditor\\benchmark tests"
    dictionaries = []
    for i in range(3):
        tests = list(range(10,110,10))
        random.shuffle(tests)
        print("running tests",tests)
        results = timeOptimizerBatch(benchmarkPath, tests)
        d = {}
        for j in range(len(tests)):
            d[tests[j]] = results[j]
            print("writing ",results[j],"to dictionary index",tests[j])
        dictionaries.append(d)
    for dictionary in dictionaries:
        print("test result:")
        for index in range(10,110,10):
            print(dictionary[index])

def make_all_subclip_folders(filenames, start_times, destinationFolderLocation):
    #figure out maximum duration
    startTime = max([start_times[i] for i in filenames])
    endTime = min([start_times[i]+audiosync.getVideoDuration(i) for i in filenames])
    print("make_all_subclip_folders start time is",startTime,"and end time is",endTime)
    duration = endTime - startTime
    print("so duration is",duration)
    for percentage in range(10, 110, 10):
        print("percentage is",percentage)
        make_subclip_folder(filenames, start_times, duration * percentage / 100, destinationFolderLocation, "test"+str(percentage))

if __name__ == "__main__":
    import gui

