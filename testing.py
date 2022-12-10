import download
import geotagsearch
import videoedit
import audiosync
import json


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



pretend1 = 'C:\\Users\\User\\Documents\\PartIIProject\\projectvideoeditor\\thepretender-CIskdB33wnw.mp4'
pretend2 = 'C:\\Users\\User\\Documents\\PartIIProject\\projectvideoeditor\\thepretender-o6xQj-a_aqI.mp4'
pretend3 = 'C:\\Users\\User\\Documents\\PartIIProject\\projectvideoeditor\\thepretender-yvb4RE2FKeY.mp4'
tsfh = "C:\\Users\\User\\Music\\two_steps_from_hell.mp3"
tsfh_delayed = "C:\\Users\\User\\Music\\two_steps_from_hell_delayed.mp3"
output = "C:\\Users\\User\\Music\\output.mp4"
if __name__ == "__main__":
    filenames = [pretend1,pretend2,pretend3]
    clips = videoedit.vidArrayFromFilenames(filenames)
    start_times = audiosync.constructTimeline(filenames)
    print(start_times)
    for i in range(len(clips)):
        clips[i] = clips[i].set_start(start_times[filenames[i]])
    combined = videoedit.viewTimeline(clips)
    combined.resize(width=480).write_videofile(output, fps=1)
