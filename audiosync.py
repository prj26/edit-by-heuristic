#!/usr/bin/env python3

# THIS CONTAINS A MODIFICATION OF SYNCSTART, WHICH IS NOT MY OWN CODE
# EACH SECTION WILL BE MARKED AS EITHER VERBATIM FROM THE ORIGINAL
# OR MARKED AS MODIFIED

# I would just import it normally, but it is necessary to modify some functions
# to ensure that correlations are strong enough to be meaningful
# and not just the highest random correlation present

#VERBATIM
"""
The steps taken by ``syncstart``:

- extract start audio as ``.wav`` using ffmpeg
- optionally normalize, denoise, lowpass the two ``.wav``
- compute offset via correlation using scipy ifft/fft
- print result and optionally show in diagrams

Requirements:

- ffmpeg installed
- Python3 with tk (tk is separate on Ubuntu: python3-tk)

References:

- https://ffmpeg.org/ffmpeg-all.html
- https://github.com/slhck/ffmpeg-normalize
- https://dsp.stackexchange.com/questions/736/how-do-i-implement-cross-correlation-to-prove-two-audio-files-are-similar

Within Python:

from syncstart import file_offset
file_offset

"""


# VERBATIM
import matplotlib

matplotlib.use('TkAgg')
from matplotlib import pyplot as plt
import numpy as np
from scipy import fft
from scipy.io import wavfile
import tempfile
import os
import pathlib
import sys

# MODIFIED: added imports for getting file duration
import cv2

# VERBATIM
__version__ = "1.0.1"
__author__ = """Roland Puntaier"""
__email__ = 'roland.puntaier@gmail.com'

# VERBATIM
# global
ax = None
take = 20
normalize = False
denoise = False
lowpass = 0

# VERBATIM
ffmpegwav = 'ffmpeg -i "{}" -t %s -c:a pcm_s16le -map 0:a "{}"'
ffmpegnormalize = ('ffmpeg -y -nostdin -i "{}" -filter_complex ' +
                   "'[0:0]loudnorm=i=-23.0:lra=7.0:tp=-2.0:offset=4.45:linear=true:print_format=json[norm0]' " +
                   "-map_metadata 0 -map_metadata:s:a:0 0:s:a:0 -map_chapters 0 -c:v copy -map '[norm0]' " +
                   '-c:a:0 pcm_s16le -c:s copy "{}"')
ffmpegdenoise = 'ffmpeg -i "{}" -af' + " 'afftdn=nf=-25' " + '"{}"'
ffmpeglow = 'ffmpeg -i "{}" -af' + " 'lowpass=f=%s' " + '"{}"'
o = lambda x: '%s%s' % (x, '.wav')


# VERBATIM
def in_out(command, infile, outfile):
    hdr = '-' * len(command)
    print("%s\n%s\n%s" % (hdr, command, hdr))
    ret = os.system(command.format(infile, outfile))
    if 0 != ret:
        sys.exit(ret)


# VERBATIM
def normalize_denoise(infile, outname):
    with tempfile.TemporaryDirectory() as tempdir:
        outfile = o(pathlib.Path(tempdir) / outname)
        in_out(ffmpegwav % take, infile, outfile)
        if normalize:
            infile, outfile = outfile, o(outfile)
            in_out(ffmpegnormalize, infile, outfile)
        if denoise:
            infile, outfile = outfile, o(outfile)
            in_out(ffmpegdenoise, infile, outfile)
            infile, outfile = outfile, o(outfile)
            in_out(ffmpegdenoise, infile, outfile)
        if int(lowpass):
            infile, outfile = outfile, o(outfile)
            in_out(ffmpeglow % lowpass, infile, outfile)
        r, s = wavfile.read(outfile)
        if len(s.shape) > 1:  # stereo
            s = s[:, 0]
        return r, s


# VERBATIM
def fig1(title=None):
    fig = plt.figure(1)
    plt.margins(0, 0.1)
    plt.grid(True, color='0.7', linestyle='-', which='major', axis='both')
    plt.grid(True, color='0.9', linestyle='-', which='minor', axis='both')
    plt.title(title or 'Signal')
    plt.xlabel('Time [seconds]')
    plt.ylabel('Amplitude')
    axs = fig.get_axes()
    global ax
    ax = axs[0]


# VERBATIM
def show1(fs, s, color=None, title=None, v=None):
    if not color: fig1(title)
    if ax and v: ax.axvline(x=v, color='green')
    plt.plot(np.arange(len(s)) / fs, s, color or 'black')
    if not color: plt.show()


# VERBATIM
def show2(fs, s1, s2, title=None):
    fig1(title)
    show1(fs, s1, 'blue')
    show1(fs, s2, 'red')
    plt.show()


# VERBATIM
def read_normalized(in1, in2):
    global normalize
    r1, s1 = normalize_denoise(in1, 'out1')
    r2, s2 = normalize_denoise(in2, 'out2')
    if r1 != r2:
        old, normalize = normalize, True
        r1, s1 = normalize_denoise(in1, 'out1')
        r2, s2 = normalize_denoise(in2, 'out2')
        normalize = old
    assert r1 == r2, "not same sample rate"
    fs = r1
    return fs, s1, s2


# MODIFIED
def corrabs(s1, s2):
    # this section is verbatim
    ls1 = len(s1)
    ls2 = len(s2)
    padsize = ls1 + ls2 + 1
    padsize = 2 ** (int(np.log(padsize) / np.log(2)) + 1)
    s1pad = np.zeros(padsize)
    s1pad[:ls1] = s1
    s2pad = np.zeros(padsize)
    s2pad[:ls2] = s2
    corr = fft.ifft(fft.fft(s1pad) * np.conj(fft.fft(s2pad)))
    ca = np.absolute(corr)
    xmax = np.argmax(ca)

    # modified to test against 90th percentile
    percent90 = np.percentile(ca, 90)
    relSpikeHeight = ca[xmax] / percent90
    return ls1, ls2, padsize, xmax, ca, relSpikeHeight


# VERBATIM
def cli_parser(**ka):
    import argparse
    parser = argparse.ArgumentParser(description=file_offset.__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version', version=__version__)

    if 'in1' not in ka:
        parser.add_argument(
            'in1',
            help='First media file to sync with second, using audio.')
    if 'in2' not in ka:
        parser.add_argument(
            'in2',
            help='Second media file to sync with first, using audio.')
    if 'take' not in ka:
        parser.add_argument(
            '-t', '--take',
            dest='take',
            action='store',
            default=20,
            help='Take X seconds of the inputs to look at. (default: 20)')
    if 'show' not in ka:
        parser.add_argument(
            '-s', '--show',
            dest='show',
            action='store_false',
            default=True,
            help='Turn off "show diagrams", in case you are confident.')
    if 'normalize' not in ka:
        parser.add_argument(
            '-n', '--normalize',
            dest='normalize',
            action='store_true',
            default=False,
            help='Turn on normalize. It turns on by itself in a second pass, if sampling rates differ.')
    if 'denoise' not in ka:
        parser.add_argument(
            '-d', '--denoise',
            dest='denoise',
            action='store_true',
            default=False,
            help='Turns on denoise, as experiment in case of failure.')
    if 'lowpass' not in ka:
        parser.add_argument(
            '-l', '--lowpass',
            dest='lowpass',
            action='store',
            default=0,
            help="lowpass, just in case, because like with manual sync'ing,\
      the low frequencies matter more. 0 == off. (default: 0)")
    return parser


# MODIFIED
def file_offset(**ka):
    """CLI interface to sync two media files using their audio streams.
    ffmpeg needs to be available.
    """

    parser = cli_parser(**ka)
    args = parser.parse_args().__dict__
    ka.update(args)

    global take, normalize, denoise, lowpass
    in1, in2, take, show = ka['in1'], ka['in2'], ka['take'], ka['show']
    normalize, denoise, lowpass = ka['normalize'], ka['denoise'], ka['lowpass']
    fs, s1, s2 = read_normalized(in1, in2)

    # modified to unpack relSpikeHeight
    ls1, ls2, padsize, xmax, ca, relSpikeHeight = corrabs(s1, s2)

    if show: show1(fs, ca, title='Correlation', v=xmax / fs)
    sync_text = """
==============================================================================
%s needs 'ffmpeg -ss %s' cut to get in sync
==============================================================================
"""
    if xmax > padsize // 2:
        if show: show2(fs, s1, s2[padsize - xmax:], title='1st=blue;2nd=red=cut(%s;%s)' % (in1, in2))
        file, offset = in2, (padsize - xmax) / fs
    else:
        if show: show2(fs, s1[xmax:], s2, title='1st=blue=cut;2nd=red (%s;%s)' % (in1, in2))
        file, offset = in1, xmax / fs
    print(sync_text % (file, offset))
    print("s1:", in1, "s2:", in2)
    print("len(s1):", len(s1), "len(s2):", len(s2), "xmax:", xmax)
    # modified to return relSpikeHeight
    return file, offset, relSpikeHeight


# (MODIFIED TO REMOVE MAIN)

# ADDITIONS
# THIS IS THE END OF THE SYNCSTART CODE
# WHAT FOLLOWS IS CODE WRITTEN BY ME EXCEPT WHERE SPECIFIED OTHERWISE

def getVideoDuration(filename):
    # taken from stackoverflow comments on answer
    # https://stackoverflow.com/questions/3844430/how-to-get-the-duration-of-a-video-in-python
    cap = cv2.VideoCapture(filename)
    framerate = cap.get(cv2.CAP_PROP_FPS)
    if framerate == 0:
        return 0
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    return duration


class ComparableLink:
    def __init__(self, song1, song2, linkStrength):
        self.song1 = song1
        self.song2 = song2
        self.linkStrength = linkStrength

    def __lt__(self, other):
        return self.linkStrength < other.linkStrength

    def __le__(self, other):
        return self.linkStrength <= other.linkStrength

    def __gt__(self, other):
        return self.linkStrength > other.linkStrength

    def __ge__(self, other):
        return self.linkStrength >= other.linkStrength

    def __eq__(self, other):
        return self.linkStrength == other.linkStrength

    def __ne__(self, other):
        return self.linkStrength != other.linkStrength

    def __repr__(self):
        return (self.song1, self.song2, self.linkStrength)


def constructTimeline(filenames, progressHook=lambda x:1):
    offset_table = {}
    # offset_table[(song,base)] = ('using base as the reference timeline, what is the offset of song?',strength)

    connected_clusters = {}
    # the set of nodes that any node is directly or indirectly connected to

    direct_connections = {}
    # the set of nodes that any node is directly connected to

    links = []
    # link of links as ComparableLink items

    durations = {name: getVideoDuration(name) for name in filenames}
    print("durations:",durations)
    for name in filenames:
        if durations[name] == 0:
            return "Could not find duration for '"+name+"' - please remove this file and try again"

    progressTotal = (len(filenames) * (len(filenames)-1))/2
    progressSoFar = 0

    for i in range(len(filenames)):
        for j in range(i):
            moredelayed, time, strength = file_offset(take=max(durations[filenames[j]],durations[filenames[i]]), in1=filenames[i], in2=filenames[j], show=False)
            if filenames[j] == moredelayed:
                time = -time
                if abs(time) > getVideoDuration(filenames[j]):
                    print("best correlation between",filenames[i],"and",filenames[j],"is out of bounds; setting strength to 0")
                    strength = 0
            else:
                if abs(time) > getVideoDuration(filenames[i]):
                    print("best correlation between",filenames[i],"and",filenames[j],"is out of bounds; setting strength to 0")
                    strength = 0
            offset_table[(filenames[i], filenames[j])] = (-time, strength)
            offset_table[(filenames[j], filenames[i])] = (time, strength)
            print("using",filenames[i],"as a base, the offset of",filenames[j],"is",time,"with strength",strength)
            links.append(ComparableLink(filenames[i], filenames[j], strength))
            progressSoFar += 1
            progressHook(progressSoFar/progressTotal)
        offset_table[(filenames[i], filenames[i])] = (0, float("inf"))
        connected_clusters[filenames[i]] = {filenames[i]}
        direct_connections[filenames[i]] = set()

    # Create minimum spanning tree from strongest links
    # such a spanning tree will contain (number of videos)-1 links
    linksLeft = len(filenames) - 1

    links.sort()
    linkIndex = len(links) - 1

    # work backwards from the end of the list, which (being sorted) will contain the strongest links
    # (number of videos minus one)

    print("starting graph construction with", linksLeft, "links left")
    while linksLeft > 0:
        # check if we can add next highest link
        nextLink = links[linkIndex]
        # add link only if it doesn't form a cycle
        if (nextLink.song1 not in connected_clusters[nextLink.song2]):
            connected_clusters[nextLink.song2].update(connected_clusters[nextLink.song1])
            # connected_clusters[nextLink.song1] = connected_clusters[nextLink.song2]
            for node in connected_clusters[nextLink.song1]:
                connected_clusters[node] = connected_clusters[nextLink.song2]
            direct_connections[nextLink.song1].add(nextLink.song2)
            direct_connections[nextLink.song2].add(nextLink.song1)
            print("making link from", nextLink.song1, "and", nextLink.song2, "(strength",
                  str(nextLink.linkStrength) + ")")
            print("connected_clusters:", connected_clusters)
            print("direct_connections:", direct_connections)
            linksLeft -= 1
        else:
            print("ignoring redundant link from", nextLink.song1, "to", nextLink.song2)
        linkIndex -= 1

    # direct_connections now describes a spanning tree: next step is to find the first video, the one with the lowest offset from any given node

    def lowest_filename_and_offset(filename, previous):
        lowestOffset = 0
        lowestFilename = filename
        for neighbour in direct_connections[filename]:
            if neighbour != previous:
                lowestFromNeighbour, lowestRelativeOffset = lowest_filename_and_offset(neighbour, filename)
                lowestAbsoluteOffset = lowestRelativeOffset + offset_table[(neighbour, filename)][0]
                if lowestAbsoluteOffset < lowestOffset:
                    lowestOffset = lowestAbsoluteOffset
                    lowestFilename = lowestFromNeighbour

        return lowestFilename, lowestOffset

    firstVideo, firstOffset = lowest_filename_and_offset(filenames[0], None)

    start_time = {}

    def calculate_start_times(filename, filenameOffset, previous):
        start_time[filename] = filenameOffset
        for neighbour in direct_connections[filename]:
            if neighbour != previous:
                calculate_start_times(neighbour, filenameOffset + offset_table[(neighbour, filename)][0], filename)

    calculate_start_times(firstVideo, 0, None)

    for filename in filenames:
        print(filename,"starts at",start_time[filename],"and ends at",start_time[filename]+durations[filename])

    return start_time
