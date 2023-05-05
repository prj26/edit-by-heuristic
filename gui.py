import pathlib
from tkinter import filedialog
from tkinter import *
from tkinter.ttk import Progressbar
from datetime import datetime, timedelta
import tempfile
import threading
import sys

import webbrowser
import geotagsearch
import download
import audiosync
import coreoptimizer
import videoedit




RESULTS_DISPLAY_LIMIT = 10

class OptimizerContent():
    def __init__(self, window, contentFrame):
        self.window = window
        self.contentFrame = contentFrame

        self.cutCostRow = Frame(contentFrame)
        self.cutCostRow.pack(anchor=W)

        self.cutCostLabel = Label(self.cutCostRow, text="Cut cost:")
        self.cutCostLabel.pack(side=LEFT)

        self.cutCostEntry = Entry(self.cutCostRow, width=5)
        self.cutCostEntry.pack(side=LEFT)

        self.selectHeuristicLabel = Label(contentFrame, text="Select Heuristic")
        self.selectHeuristicLabel.pack(anchor=W)

        self.heuristicRadioButtonIntVar = IntVar()

        self.sumHeuristicRow = Frame(contentFrame)
        self.sumHeuristicRow.pack(anchor=W)

        self.sumHeuristicRadioButton = Radiobutton(self.sumHeuristicRow, variable=self.heuristicRadioButtonIntVar, value=0)
        self.sumHeuristicRadioButton.pack(side=LEFT)

        self.sumHeuristicWeightedLabel = Label(self.sumHeuristicRow,text="Weighted sum of")
        self.sumHeuristicWeightedLabel.pack(side=LEFT)

        self.sumHeuristicFocusWeightEntry = Entry(self.sumHeuristicRow, width=5)
        self.sumHeuristicFocusWeightEntry.pack(side=LEFT)

        self.sumHeuristicFocusLabel = Label(self.sumHeuristicRow, text="focus heuristic and")
        self.sumHeuristicFocusLabel.pack(side=LEFT)

        self.sumHeuristicBrightnessWeightEntry = Entry(self.sumHeuristicRow, width=5)
        self.sumHeuristicBrightnessWeightEntry.pack(side=LEFT)

        self.sumHeuristicBrightnessLabel = Label(self.sumHeuristicRow, text="image brightness")
        self.sumHeuristicBrightnessLabel.pack(side=LEFT)

        self.productHeuristicRow = Frame(contentFrame)
        self.productHeuristicRow.pack(anchor=W)

        self.productHeuristicRadioButton = Radiobutton(self.productHeuristicRow, variable=self.heuristicRadioButtonIntVar, value=1)
        self.productHeuristicRadioButton.pack(side=LEFT)

        self.productHeuristicLabel = Label(self.productHeuristicRow, text="Product of brightness and focus")
        self.productHeuristicLabel.pack()

        self.feedbackLabel = Label(contentFrame,text="")
        self.feedbackLabel.pack(anchor=W)

        self.runButtonRow = Frame(contentFrame)
        self.runButtonRow.pack(anchor=W)

        self.runButton = Button(self.runButtonRow, text="Run", command=self.onRunButton)
        self.runButton.pack(side=LEFT)

        self.batchTickBoxVar = BooleanVar()
        self.batchTickBox = Checkbutton(self.runButtonRow, variable=self.batchTickBoxVar)
        self.batchTickBox.pack(side=LEFT)

        self.batchLabel = Label(self.runButtonRow, text="Batch")
        self.batchLabel.pack(side=LEFT)

        self.nFramesEntry = Entry(self.runButtonRow, width=5)
        self.nFramesEntry.pack(side=LEFT)

        self.framesTogetherLabel = Label(self.runButtonRow, text="frames together")
        self.framesTogetherLabel.pack(side=LEFT)

        self.progressBar = Progressbar(contentFrame, orient='horizontal', mode='determinate')
        self.progressBar.pack(anchor=W, fill=X)

        self.optimizationInProgress = False
        self.nextStageReady = False

    def destroy(self):

        self.cutCostRow.destroy()

        self.cutCostLabel.destroy()

        self.cutCostEntry.destroy()

        self.selectHeuristicLabel.destroy()

        self.sumHeuristicRow.destroy()

        self.sumHeuristicRadioButton.destroy()

        self.sumHeuristicWeightedLabel.destroy()

        self.sumHeuristicFocusWeightEntry.destroy()

        self.sumHeuristicFocusLabel.destroy()

        self.sumHeuristicBrightnessWeightEntry.destroy()

        self.sumHeuristicBrightnessLabel.destroy()

        self.productHeuristicRow.destroy()

        self.productHeuristicRadioButton.destroy()

        self.productHeuristicLabel.destroy()


        self.runButtonRow.destroy()

        self.runButton.destroy()

        self.batchTickBox.destroy()

        self.batchLabel.destroy()

        self.nFramesEntry.destroy()

        self.framesTogetherLabel.destroy()

        self.progressBar.destroy()

    def onSetFocus(self):
        self.window.setNextButtonUsable(self.nextStageReady)
        self.window.setBackButtonUsable(not self.optimizationInProgress)

    def setFeedback(self,text):
        self.feedbackLabel['text'] = text

    def onRunButton(self):
        print("run button pressed")
        cutCostString = self.cutCostEntry.get()
        try:
            cutCostFloat = float(cutCostString)
        except:
            self.setFeedback("Couldn't convert '%s' to float" % cutCostString)
            return
        heuristicIsSum = self.heuristicRadioButtonIntVar.get() == 0
        if heuristicIsSum:
            focusWeightString = self.sumHeuristicFocusWeightEntry.get()
            try:
                focusWeightFloat = float(focusWeightString)
            except:
                self.setFeedback("Couldn't convert '%s' to float" % focusWeightString)
                return
            brightnessWeightString = self.sumHeuristicBrightnessWeightEntry.get()
            try:
                brightnessWeightFloat = float(brightnessWeightString)
            except:
                self.setFeedback("Couldn't convert '%s' to float" % brightnessWeightString)
                return
            heuristic = lambda frame,duration:((coreoptimizer.tenegrad_sobel_heuristic(frame, duration)*focusWeightFloat)+(coreoptimizer.brightheuristic(frame, duration)*brightnessWeightFloat))
        else:
            heuristic = lambda frame,duration:(coreoptimizer.tenegrad_sobel_heuristic(frame, duration) * coreoptimizer.brightheuristic(frame, duration))

        shouldBatchFramesTogether = self.batchTickBoxVar.get()
        if shouldBatchFramesTogether:
            nFramesString = self.nFramesEntry.get()
            try:
                nFramesInt = int(nFramesString)
            except:
                self.setFeedback("Couldn't convert '%s' to a positive integer")
                return
        else:
            nFramesInt = 1

        x = threading.Thread(target=self.optimizerThread, args=(heuristic, cutCostFloat, nFramesInt),daemon=True)
        x.start()

    def optimizerThread(self, heuristic, cutCost, nFrames):
        self.optimizationInProgress = True
        self.setFeedback("Running...")
        try:
            #clipsDict = videoedit.vidDictionaryFromFilenames(self.window.infoDict["filenames"])
            optimizer = coreoptimizer.FrameTimelinesOptimizer(self.window.infoDict["filenames"], self.window.infoDict["start_times"])
            result = optimizer.optimizeWithFixedCosts(heuristic, cutCost, nFrames, self.progressHook)
            self.cut_history = result.cutHistory
            self.progressHook(1)
            self.optimizationInProgress = False
            self.nextStageReady = True
            self.setFeedback("Finished")
            self.onSetFocus()
        except:
            self.setFeedback("Encountered an error while optimizing")
            raise

    def progressHook(self, value):
        self.progressBar['value'] = value*100

    def getInfoDict(self):
        return {"cut_history":self.cut_history}

class AudioSyncContent():
    def __init__(self, window, contentFrame):
        #todo: make state visible
        self.window = window
        self.contentFrame = contentFrame
        self.syncFinished = False

        self.progressBar = Progressbar(contentFrame, orient='horizontal', mode='determinate')
        self.progressBar.pack(anchor="w", fill=X)

        self.feedback = Label(contentFrame, text="Syncing...")
        self.feedback.pack(anchor="w")

        self.syncedFilesFrame = Frame(contentFrame)
        self.syncedFilesFrame.pack(anchor="w")

        self.syncedFiles = []
        for filename in window.infoDict["filenames"]:
            newSyncedFile = SyncedFile(self.syncedFilesFrame, filename)
            self.syncedFiles.append(newSyncedFile)
            newSyncedFile.pack()

        self.startAudioSyncProcess()

    def destroy(self):
        self.progressBar.destroy()
        self.feedback.destroy()
        self.syncedFilesFrame.destroy()
        for syncedFile in self.syncedFiles:
            syncedFile.destroy()


    def onSetFocus(self):
        self.window.setNextButtonUsable(self.syncFinished)
        self.window.setNextButtonUsable(self.syncFinished)

    def startAudioSyncProcess(self):
        if len(self.window.infoDict["filenames"]) > 0:
            x = threading.Thread(target=self.audioSyncThread, daemon=True)
            x.start()
            print("download process started")
        else:
            print("could not start syncing")

    def setFeedback(self, text):
        self.feedback["text"] = text

    def audioSyncThread(self):
        self.onSetFocus()
        print("constructing timelines...")
        self.start_times = audiosync.constructTimeline(self.window.infoDict["filenames"],self.progressHook)
        if type(self.start_times) == str:
            self.progressHook(0)
            self.setFeedback(self.start_times)
            self.window.setBackButtonUsable(True)
            return
        self.progressHook(1.0)
        self.syncFinished = True
        self.setFeedback("Audio Sync Finished.")
        for syncedFile in self.syncedFiles:
            syncedFile.setText(str(self.start_times[syncedFile.filename]))
        self.onSetFocus()

    def progressHook(self, value):
        self.progressBar['value'] = value*100

    def getInfoDict(self):
        d = {}
        for syncedFile in self.syncedFiles:
            syncedFileString = syncedFile.get()
            try:
                syncedFileFloat = float(syncedFileString)
            except:
                print("")
                return {"start_times":{}}
            d[syncedFile.filename] = syncedFileFloat
        return {"start_times":d}

class SyncedFile():
    def __init__(self, outerFrame, labelText):
        self.outerFrame = outerFrame
        self.labelText = labelText
        self.filename = labelText
        self.innerFrame = Frame(self.outerFrame)
        self.label = Label(self.innerFrame, text=labelText)
        self.entryBox = Entry(self.innerFrame)

    def pack(self):
        self.innerFrame.pack(anchor=W)
        self.label.pack(side=LEFT)
        self.entryBox.pack(side=LEFT)

    def setText(self,text):
        self.entryBox.delete(0, END)
        self.entryBox.insert(0,text)

    def destroy(self):
        self.innerFrame.destroy()
        self.label.destroy()
        self.entryBox.destroy()

    def get(self):
        return self.entryBox.get()

class ExportContent():
    def __init__(self, window, contentFrame):
        self.window = window
        self.contentFrame = contentFrame

        self.exportInProgress = False

        self.widthFrame = Frame(contentFrame)
        self.widthFrame.pack(anchor="w")

        self.widthLabel = Label(self.widthFrame, text="Output width (pixels):")
        self.widthLabel.pack(side=LEFT)

        self.widthEntry = Entry(self.widthFrame, width=5)
        self.widthEntry.insert(END, "480")
        self.widthEntry.pack(side=LEFT)

        self.fadeFrame = Frame(contentFrame)
        self.fadeFrame.pack(anchor="w")

        self.fadeLabel = Label(self.fadeFrame, text="Audio fade time across cuts (seconds):")
        self.fadeLabel.pack(side=LEFT)

        self.fadeEntry = Entry(self.fadeFrame, width=5)
        self.fadeEntry.insert(END, "5")
        self.fadeEntry.pack(side=LEFT)

        self.fpsFrame = Frame(contentFrame)
        self.fpsFrame.pack(anchor="w")

        self.fpsLabel = Label(self.fpsFrame, text="Output FPS:")
        self.fpsLabel.pack(side=LEFT)

        self.fpsEntry = Entry(self.fpsFrame, width=5)
        self.fpsEntry.insert(END, "30")
        self.fpsEntry.pack(side=LEFT)

        self.feedbackLabel = Label(contentFrame, text="")
        self.feedbackLabel.pack(anchor="w")

        self.renderButton = Button(contentFrame, text="Render", command=self.onRenderButton)
        self.renderButton.pack(anchor="w")

        self.progressBar = Progressbar(contentFrame, orient='horizontal', mode='determinate')
        self.progressBar.pack(anchor=W, fill=X)

        self.onSetFocus()

    def setFeedback(self, string):
        self.feedbackLabel["text"] = string

    def onSetFocus(self):
        self.window.setNextButtonUsable(False)
        self.window.setBackButtonUsable(not self.exportInProgress)

    def onRenderButton(self):
        print("render button clicked, here's the info dict")
        print(window.infoDict)
        widthString = self.widthEntry.get()
        # valdate user width input
        try:
            widthInt = int(widthString)
            assert(widthInt > 0 and widthInt < 100000)
        except:
            self.setFeedback("The output width must be between 0 and 100,000")
            return

        fadeString = self.fadeEntry.get()
        #validate user audio fade time input
        try:
            fadeFloat = int(fadeString)
            assert(fadeFloat >= 0)
        except:
            self.setFeedback("The audio fade time must be a real value greater than 0")
            return

        fpsString = self.fpsEntry.get()
        #validate user fps input
        try:
            fpsFloat = float(fpsString)
            assert(fpsFloat>0)
        except:
            self.setFeedback("The output fps must be a real number greater than 0")
            return

        #get output destination
        outputPath = filedialog.asksaveasfilename(title="output.mp4",filetypes=(("MP4 files","*.mp4"),), defaultextension=".mp4")

        if outputPath == "":
            return

        self.exportInProgress = True
        clipsDict = videoedit.vidDictionaryFromFilenames(window.infoDict["filenames"])


        #Used for skipping the optimisation stage during testing
        debug = False
        if debug:
            #pick two videos to cut between
            vid1 = window.infoDict["filenames"][0]
            vid2 = window.infoDict["filenames"][1]
            if window.infoDict["start_times"][vid1] < window.infoDict["start_times"][vid2]:
                #vid1 starts earlier, flip at the moment that vid2 starts
                cutTime = window.infoDict["start_times"][vid2]
                cut = coreoptimizer.Cut(cutTime,vid1,cutTime,vid2)
            else:
                #vid2 starts earlier
                cutTime = window.infoDict["start_times"][vid1]
                cut = coreoptimizer.Cut(cutTime,vid2,cutTime,vid1)
            cutlist = [cut]
        #DEBUG END
        else:
            cutlist = self.window.infoDict["cut_history"]

        self.startRenderProcess(clipsDict, cutlist, fadeFloat, widthInt, fpsFloat, outputPath)

    def startRenderProcess(self, clipsDict, cutlist, fadeFloat, widthInt, fpsFloat, outputPath):
        x = threading.Thread(target=self.renderThread, daemon=True, args=(clipsDict, cutlist, fadeFloat, widthInt, fpsFloat, outputPath))
        x.start()
        print("render process started")



    def renderThread(self, clipsDict, cutlist, fadeFloat, widthInt, fpsFloat, outputPath):
        print("thread started")
        combined = videoedit.renderVideoFromCutList(clipsDict, cutlist, window.infoDict["start_times"], maxFade=fadeFloat)

        self.audioProportion = 0.2

        self.oldstderr = sys.stderr
        try:
            self.renderButton["state"] = DISABLED
            sys.stderr = self
            self.setFeedback("Rendering...")
            combined.resize(width=widthInt).write_videofile(outputPath, fps=fpsFloat)
            self.setFeedback("Finished rendering output to "+outputPath)
        except Exception as err:
            sys.stderr = self.oldstderr
            raise err

        finally:
            self.renderButton["state"] = NORMAL
            sys.stderr = self.oldstderr


        self.setBarProgress(1.0)
        self.exportInProgress = False

    def write(self, text):
        #check if output matches audio format
        if text.startswith("\rchunk:"):
            #format is audio
            numerator = int(text.split("/")[0].split("|")[2].strip())
            denominator = int(text.split("/")[1].split("[")[0].strip())
            fraction = numerator/denominator
            progress = self.audioProportion * fraction
            self.setBarProgress(progress)

            #get ETA
            eta = text.split("[")[1].split(",")[0]
            self.setFeedback("(1/2)Rendering audio for "+eta)
        elif text.startswith("\rt:"):
            #format is video
            numerator = int(text.split("/")[0].split("|")[2].strip())
            denominator = int(text.split("/")[1].split("[")[0].strip())
            fraction = numerator/denominator
            progress = self.audioProportion + (fraction * (1 - self.audioProportion))
            self.setBarProgress(progress)

            #get ETA
            eta = text.split("[")[1].split(",")[0]
            self.setFeedback("(2/2)Rendering video for "+eta)
        self.oldstderr.write(text)

    def flush(self):
        self.oldstderr.flush()

    def setBarProgress(self, value):
        self.progressBar['value'] = value*100


    def destroy(self):
        self.widthFrame.destroy()
        self.widthLabel.destroy()
        self.widthEntry.destroy()
        self.fadeFrame.destroy()
        self.fadeLabel.destroy()
        self.fadeEntry.destroy()
        self.fpsFrame.destroy()
        self.fpsLabel.destroy()
        self.fpsEntry.destroy()
        self.feedbackLabel.destroy()
        self.renderButton.destroy()
        self.progressBar.destroy()

class DownloadContent():
    def __init__(self, window, contentFrame):
        self.window = window
        self.contentFrame = contentFrame

        self.downloadingInfoLabel = Label(contentFrame, text="Downloading...")
        self.downloadingInfoLabel.pack(anchor="w")

        self.mainProgressBar = Progressbar(contentFrame, orient='horizontal', mode='determinate')
        self.mainProgressBar.pack(anchor="w", fill=X)

        self.twoBarsGrid = Frame(contentFrame)
        self.twoBarsGrid.pack(anchor="w", expand=1, fill=BOTH)

        self.downloadedLabel = Label(self.twoBarsGrid, text="Downloaded")
        self.downloadedLabel.grid(row=0, column=0, sticky="w")

        self.downloadingLeftFrame = Frame(self.twoBarsGrid, relief=SUNKEN, borderwidth=2)
        self.downloadingLeftFrame.grid(row=1, column=0, sticky="nesw")

        self.manualFilesButton  = Button(self.twoBarsGrid, text="Add manually", command=self.onAddManual)
        self.manualFilesButton.grid(row=0, column=2, sticky="w")

        self.manualFilesFrame = Frame(self.twoBarsGrid, relief=SUNKEN, borderwidth=2)
        self.manualFilesFrame.grid(row=1, column=2, sticky="nesw")

        self.filesInnerSeparator = Frame(self.twoBarsGrid)
        self.filesInnerSeparator.grid(row=0, column=1, columnspan=1, rowspan=2, sticky="nesw")

        self.twoBarsGrid.columnconfigure(0, weight=5)
        self.twoBarsGrid.columnconfigure(1, weight=1)
        self.twoBarsGrid.columnconfigure(2, weight=5)
        self.twoBarsGrid.rowconfigure(1, weight=1)

        self.downloadFinished = False
        self.downloadedVideos = []
        self.manualVideos = []
        self.filenamesDownloaded = []

        for i in range(len(window.infoDict["urls"])):
            self.downloadedVideos.append(DownloadingVideo(self.downloadingLeftFrame, window.infoDict["urls"][i], window.infoDict["titles"][i], "..."))
            self.downloadedVideos[-1].pack()

        self.onSetFocus()
        self.hasPrintedDictionary = False
        self.startDownloadProcess()

    def onSetFocus(self):
        self.window.setNextButtonUsable(self.downloadFinished and (len(self.downloadedVideos) + len(self.manualVideos)) > 1)
        self.window.setBackButtonUsable(self.downloadFinished)

    def onAddManual(self):
        path = filedialog.askopenfilename(initialdir = "/", title="Select file", filetypes=[("mp4 files",".mp4"),("webm files",".webm"),("All files","*")], defaultextension=".mp4")
        if path != "":
            newVid = SelectableVideo(self.manualFilesFrame, path, path.split("/")[-1], "x", (lambda:1))
            newVid.onButtonPress = lambda newVid=newVid:self.removeFromManual(newVid)
            self.manualVideos.append(newVid)
            newVid.pack()
        self.onSetFocus()

    def removeFromManual(self, manualVideo):
        self.manualVideos.remove(manualVideo)
        manualVideo.destroy()
        self.onSetFocus()

    def startDownloadProcess(self):
        if len(self.window.infoDict["urls"]):
            x = threading.Thread(target=self.downloadThread, daemon=True)
            x.start()
            print("download process started")
        else:
            self.downloadFinished = True
            self.onSetFocus()

    def downloadThread(self):
        try:
            self.videoConstant = 0
            self.videoMultiplier = 1 / len(self.window.infoDict["urls"])
            self.videoCount = 0
            self.filenamesDownloaded = []
            for url in self.window.infoDict["urls"]:
                path = window.temp_path / ("vid" + str(self.videoCount) + ".mp4")
                path = str(path)
                print("using the string", repr(path), "as the path")
                download.downloadURL(url, path, self.downloadProgressHook)
                self.videoCount += 1
                self.videoConstant = (self.videoMultiplier * self.videoCount)
                self.filenamesDownloaded.append(path)
            self.downloadFinished = True
            self.onSetFocus()
        except:
            print("download failed, here#s why")
            raise

    def downloadProgressHook(self, dictionary):
        if not self.hasPrintedDictionary:
            individualValue = float(dictionary['_percent_str'].split("%")[0])
            print("videoConstant is",self.videoConstant)
            self.mainProgressBar['value'] = (self.videoConstant*100) + (self.videoMultiplier * individualValue)
            self.downloadedVideos[self.videoCount].progressBar['value'] = individualValue

    def destroy(self):
        self.downloadingInfoLabel.destroy()
        self.twoBarsGrid.destroy()
        self.downloadedLabel.destroy()
        self.mainProgressBar.destroy()
        self.downloadingLeftFrame.destroy()
        self.manualFilesButton.destroy()
        self.manualFilesFrame.destroy()
        self.filesInnerSeparator.destroy()
        self.filesInnerSeparator.destroy()
        for downloadingVideo in self.downloadedVideos:
            downloadingVideo.destroy()

    def getInfoDict(self):
        filenames = []
        for filename in self.filenamesDownloaded:
            filenames.append(filename)
        for manualVideo in self.manualVideos:
            filenames.append((manualVideo.url))
        return {"filenames":filenames}

class GeotagSearchContent():
    def __init__(self, window, contentFrame):
        self.mainColumnFrame = contentFrame
        self.window = window

        self.locationParametersFrame = Frame(self.mainColumnFrame)

        self.leftlocationParameterFrame = Frame(self.locationParametersFrame)

        self.searchLocationLabel = Label(self.leftlocationParameterFrame, text="Search location")

        self.searchLocationEntry = Entry(self.leftlocationParameterFrame, width=40)

        self.rightlocationParameterFrame = Frame(self.locationParametersFrame, padx=10)

        self.searchRadiusLabel = Label(self.rightlocationParameterFrame, text="Radius (km)")

        self.searchRadiusEntry = Entry(self.rightlocationParameterFrame)

        self.searchLocationCoordsFeedback = Label(self.mainColumnFrame, text="")

        self.songNameLabel = Label(self.mainColumnFrame, text="Song name")

        self.searchQueryFrame = Frame(self.mainColumnFrame)

        self.searchEntryBox = Entry(self.searchQueryFrame, width=40)

        self.useDatetimeVar = BooleanVar()
        self.useDatetimeTickbox = Checkbutton(self.searchQueryFrame, variable=self.useDatetimeVar)

        self.searchWithinLabel = Label(self.searchQueryFrame, text="Within ")

        self.searchDayCount = Entry(self.searchQueryFrame, width=3)

        self.searchDaysOfLabel = Label(self.searchQueryFrame, text=" days after ")

        self.searchDateDaysEntry = Entry(self.searchQueryFrame, width=2)

        self.searchSlash1 = Label(self.searchQueryFrame, text="/")

        self.searchDateMonthEntry = Entry(self.searchQueryFrame, width=2)

        self.searchSlash2 = Label(self.searchQueryFrame, text="/")

        self.searchDateYearEntry = Entry(self.searchQueryFrame, width=4)

        self.matchesExactlyFrame = Frame(self.mainColumnFrame)

        self.matchesExactlyVar = BooleanVar()
        self.matchesExactlyTickbox = Checkbutton(self.matchesExactlyFrame, variable=self.matchesExactlyVar)

        self.matchesExactlyLabel = Label(self.matchesExactlyFrame,
                                         text="Result video titles must contain query keywords")

        self.searchButtonFrame = Frame(self.mainColumnFrame)

        self.searchButton = Button(self.searchButtonFrame, text="Search", command=self.onSearchButton)

        self.resultsOuterFrame = Frame(self.mainColumnFrame)
        self.resultsOuterFrame.rowconfigure(1, weight=1)

        self.resultsOuterFrame.columnconfigure(0, weight=5)
        self.resultsOuterFrame.columnconfigure(1, weight=1)
        self.resultsOuterFrame.columnconfigure(2, weight=5)

        self.searchResultsLabel = Label(self.resultsOuterFrame, text="Search results")
        self.searchResultsFrame = Frame(self.resultsOuterFrame, relief=SUNKEN, borderwidth=2)
        self.addAllButton = Button(self.resultsOuterFrame, text="Add all", command=self.onAddAllButton)

        self.resultsInnerSeparator = Frame(self.resultsOuterFrame)

        self.selectedVideosLabel = Label(self.resultsOuterFrame, text="Selected Videos")
        self.selectedVideoUrls = Frame(self.resultsOuterFrame, relief=SUNKEN, borderwidth=2)
        self.selectedVideoOptionsFrame = Frame(self.resultsOuterFrame)
        self.removeAllButton = Button(self.selectedVideoOptionsFrame, text="Remove all", command=self.onRemoveAllButton)
        self.fromUrlButton = Button(self.selectedVideoOptionsFrame, text="From Url:", command=self.onFromUrlButton)
        self.fromUrlEntry = Entry(self.selectedVideoOptionsFrame)

        self.searchResultSelectableVideos = []
        self.selectedVideos = []
        self.pack()

        self.onSetFocus()

    def onSetFocus(self):
        self.window.setNextButtonUsable(True)
        self.window.setBackButtonUsable(False)

    def setCoordFeedback(self, string=""):
        self.searchLocationCoordsFeedback["text"] = string

    def onSearchButton(self):
        print("search button pressed")
        locationString = self.searchLocationEntry.get()
        geocode_results = geotagsearch.geocode(locationString)
        if len(geocode_results) == 0:
            self.setCoordFeedback("No location results for '" + locationString + "'")
            return
        location = geocode_results[0]
        coords = geotagsearch.coordsFromGeocodeResult(location)
        self.setCoordFeedback(str(coords))

        songName = self.searchEntryBox.get()

        dateBoundaryRequired = self.useDatetimeVar.get()
        mustMatchExactly = self.matchesExactlyVar.get()

        radiusString = self.searchRadiusEntry.get()
        try:
            radiusFloat = float(radiusString)
            assert (radiusFloat > 0)
        except:
            self.setCoordFeedback("Could not convert '" + radiusString + "' to a positive nonzero float")
            return

        if dateBoundaryRequired:
            xString = self.searchDayCount.get()
            try:
                xInt = int(xString)
                assert (xInt > 0)
            except:
                self.setCoordFeedback("Could not convert '" + xString + "' to a positive nonzero integer")
                return

            ddString = self.searchDateDaysEntry.get()
            mmString = self.searchDateMonthEntry.get()
            yyyyString = self.searchDateYearEntry.get()
            combined_dateString = ddString + "/" + mmString + "/" + yyyyString
            try:
                date_obj = datetime.strptime(combined_dateString, "%d/%m/%y")
            except:
                try:
                    date_obj = datetime.strptime(combined_dateString, "%d/%m/%Y")
                except:
                    self.setCoordFeedback("Coudn't convert '" + combined_dateString + "' into a valid date")
                    return

            date1 = date_obj - timedelta(days=1)
            date2 = date_obj + timedelta(days=xInt)

            if mustMatchExactly:
                func = lambda item: geotagsearch.filterByTitleAndDate(item, songName, date1, date2)
            else:
                func = lambda item: geotagsearch.filterByDate(item, date1, date2)
        else:
            if mustMatchExactly:
                func = lambda item: geotagsearch.filterByVideoTitle(item, songName)
            else:
                func = lambda item: True

        results, items = geotagsearch.urlsAndItemsFromSearchWithFilter(func, songName,
                                                                       str(coords[0]) + ", " + str(coords[1]),
                                                                       str(radiusFloat) + "km", 120)

        #remove duplicates
        resultsdict = {}
        for result, item in zip(results, items):
            resultsdict[result] = item

        results = list(resultsdict.keys())
        items = [resultsdict[result] for result in results]

        import json
        print(json.dumps(items[0], indent=4))
        for i in range(min(10, len(results))):
            title = items[i]["snippet"]["title"]
            max_title = 60
            if len(title) > max_title:
                title = title[:max_title] + "..."
                print("title too long, truncating to", title)

            newSelectable = SelectableVideo(self.searchResultsFrame, "https://www.youtube.com/watch?v=" + results[i],
                                            title, "+", lambda: 1)
            newSelectable.onButtonPress = lambda newSelectable=newSelectable: self.addToSelected(newSelectable)
            self.searchResultSelectableVideos.append(newSelectable)
            newSelectable.pack()

    def onAddAllButton(self):
        for selectableVideo in list([i for i in self.searchResultSelectableVideos]):
            self.addToSelected(selectableVideo)

    def addToSelected(self, selectedVideo):
        newSelected = SelectableVideo(self.selectedVideoUrls, selectedVideo.url, selectedVideo.title, "x", lambda: 1)
        newSelected.onButtonPress = lambda newSelected=newSelected: self.removeFromSelected(newSelected)
        self.selectedVideos.append(newSelected)
        newSelected.pack()
        self.searchResultSelectableVideos.remove(selectedVideo)
        selectedVideo.destroy()
        #self.window.setNextButtonUsable(True)

    def removeFromSelected(self, selectedVideo):
        self.selectedVideos.remove(selectedVideo)
        selectedVideo.destroy()
        if len(self.selectedVideos) == 0:
            #self.window.setNextButtonUsable(False)
            pass

    def onRemoveAllButton(self):
        for selectedVideo in list([i for i in self.selectedVideos]):
            self.removeFromSelected(selectedVideo)

    def onFromUrlButton(self):
        url = self.fromUrlEntry.get()
        newSelected = SelectableVideo(self.selectedVideoUrls, url, '"' + url + '"', "x", lambda: 1)
        newSelected.onButtonPress = lambda newSelected=newSelected: self.removeFromSelected(newSelected)
        self.selectedVideos.append(newSelected)
        newSelected.pack()
        #self.window.setNextButtonUsable(True)

    def pack(self):
        self.locationParametersFrame.pack(anchor=W)
        self.leftlocationParameterFrame.pack(side=LEFT)
        self.searchLocationLabel.pack(anchor=W)
        self.searchLocationEntry.pack(anchor=W)
        self.rightlocationParameterFrame.pack(side=LEFT)
        self.searchRadiusLabel.pack(anchor=W)
        self.searchRadiusEntry.pack(anchor=W)
        self.searchLocationCoordsFeedback.pack(anchor=W)
        self.songNameLabel.pack(anchor=W)
        self.searchQueryFrame.pack(anchor=W)
        self.searchEntryBox.pack(side=LEFT)
        self.useDatetimeTickbox.pack(side=LEFT)
        self.searchWithinLabel.pack(side=LEFT)
        self.searchDayCount.pack(side=LEFT)
        self.searchDaysOfLabel.pack(side=LEFT)
        self.searchDateDaysEntry.pack(side=LEFT)
        self.searchSlash1.pack(side=LEFT)
        self.searchDateMonthEntry.pack(side=LEFT)
        self.searchSlash2.pack(side=LEFT)
        self.searchDateYearEntry.pack(side=LEFT)
        self.matchesExactlyFrame.pack(anchor=W)
        self.matchesExactlyTickbox.pack(side=LEFT)
        self.matchesExactlyLabel.pack(side=LEFT)
        self.searchButtonFrame.pack(anchor=W)
        self.searchButton.pack(side=LEFT)

        self.resultsOuterFrame.pack(anchor=W, expand=1, fill=BOTH)

        self.searchResultsLabel.grid(row=0, column=0, sticky="w", pady=2)

        self.searchResultsFrame.grid(row=1, column=0, sticky="nesw", pady=2)

        self.addAllButton.grid(row=2, column=0, pady=2, sticky="w")

        self.resultsInnerSeparator.grid(row=0, column=1, columnspan=1, rowspan=3, sticky="nesw")

        self.selectedVideosLabel.grid(row=0, column=2, sticky="w", pady=2)

        self.selectedVideoUrls.grid(row=1, column=2, sticky="nesw", pady=2)

        self.selectedVideoOptionsFrame.grid(row=2, column=2, sticky="ew", pady=2)
        self.removeAllButton.pack(side=LEFT)
        self.fromUrlEntry.pack(side=RIGHT)
        self.fromUrlButton.pack(side=RIGHT)

        for selectableVideo in self.searchResultSelectableVideos:
            selectableVideo.pack()
        for selectableVideo in self.selectedVideos:
            selectableVideo.pack()

    def destroy(self):
        self.locationParametersFrame.destroy()
        self.leftlocationParameterFrame.destroy()
        self.searchLocationLabel.destroy()
        self.searchLocationEntry.destroy()
        self.rightlocationParameterFrame.destroy()
        self.searchRadiusLabel.destroy()
        self.searchRadiusEntry.destroy()
        self.searchLocationCoordsFeedback.destroy()
        self.songNameLabel.destroy()
        self.searchQueryFrame.destroy()
        self.searchEntryBox.destroy()
        self.useDatetimeTickbox.destroy()
        self.searchWithinLabel.destroy()
        self.searchDayCount.destroy()
        self.searchDaysOfLabel.destroy()
        self.searchDateDaysEntry.destroy()
        self.searchSlash1.destroy()
        self.searchDateMonthEntry.destroy()
        self.searchSlash2.destroy()
        self.searchDateYearEntry.destroy()
        self.matchesExactlyFrame.destroy()
        self.matchesExactlyTickbox.destroy()
        self.matchesExactlyLabel.destroy()
        self.searchButtonFrame.destroy()
        self.searchButton.destroy()

        self.resultsOuterFrame.destroy()

        self.searchResultsLabel.destroy()

        self.searchResultsFrame.destroy()

        self.addAllButton.destroy()

        self.resultsInnerSeparator.destroy()

        self.selectedVideosLabel.destroy()

        self.selectedVideoUrls.destroy()

        self.selectedVideoOptionsFrame.destroy()
        self.removeAllButton.destroy()
        self.fromUrlEntry.destroy()
        self.fromUrlButton.destroy()

        for selectableVideo in self.searchResultSelectableVideos:
            selectableVideo.destroy()
        for selectableVideo in self.selectedVideos:
            selectableVideo.destroy()

    def getInfoDict(self):
        d = {}
        urls = []
        titles = []
        for selectedVideo in self.selectedVideos:
            urls.append(selectedVideo.url)
            titles.append(selectedVideo.title)
        d["urls"] = urls
        d["titles"] = titles
        return d

class SelectableVideo():
    def __init__(self, outerFrame, url, title, buttonchar, onButtonPress):
        self.onButtonPress = onButtonPress
        self.outerFrame = outerFrame
        self.innerFrame = Frame(outerFrame, borderwidth=1, relief=RAISED)
        self.innerLeftFrame = Frame(self.innerFrame)
        self.titleText = Label(self.innerLeftFrame, text=title)
        self.title = title
        self.urlButton = Button(self.innerLeftFrame, text=url, command=self.onUrlPress)
        self.url = url
        self.rightButton = Button(self.innerFrame, text=" " + buttonchar + " ", command=self._onButtonPress)

    def _onButtonPress(self):
        self.onButtonPress()

    def pack(self):
        self.rightButton.pack(anchor=E, side=RIGHT, expand=1, fill=Y)
        self.innerFrame.pack(side=TOP, anchor=W, fill=X)
        self.innerLeftFrame.pack(side=LEFT, expand=1, fill=X)
        self.titleText.pack(anchor=W)
        self.urlButton.pack(anchor=W)

    def onUrlPress(self):
        webbrowser.open(self.url, new=2)

    def destroy(self):
        self.innerFrame.destroy()
        self.innerLeftFrame.destroy()
        self.titleText.destroy()
        self.urlButton.destroy()
        self.rightButton.destroy()

class DownloadingVideo():
    def __init__(self, outerFrame, url, title, endText):
        self.outerFrame = outerFrame
        self.innerFrame = Frame(outerFrame, borderwidth=1, relief=RAISED)
        self.innerLeftFrame = Frame(self.innerFrame)
        self.titleText = Label(self.innerLeftFrame, text=title)
        self.title = title
        self.urlButton = Button(self.innerLeftFrame, text=url, command=self.onUrlPress)
        self.url = url
        self.progressBar = Progressbar(self.innerLeftFrame)

        # self.rightText = Frame(self.innerFrame, text=endText)

    def pack(self):
        # self.rightText.pack(anchor=E, side=RIGHT, expand=1, fill=Y)
        self.innerFrame.pack(side=TOP, anchor=W, fill=X)
        self.innerLeftFrame.pack(side=LEFT, expand=1, fill=X)
        self.titleText.pack(anchor=W)
        self.urlButton.pack(anchor=W)
        self.progressBar.pack(anchor=W, fill=X)

    def onUrlPress(self):
        webbrowser.open(self.url, new=2)

    def destroy(self):
        self.innerFrame.destroy()
        self.innerLeftFrame.destroy()
        self.titleText.destroy()
        self.urlButton.destroy()
        self.progressBar.destroy()
        # self.rightText.destroy()

class Window():
    def __init__(self, root, temp_path):
        self.root = root
        self.temp_path = temp_path
        self.values = {}
        self.backNextFrame = Frame(root)
        self.backNextFrame.pack()

        self.backButton = Button(self.backNextFrame, text="< Back", command=self.onBackButton)
        self.backButton.pack(side=LEFT)

        self.nextButton = Button(self.backNextFrame, text="Next >", command=self.onNextButton)
        self.nextButton.pack(side=LEFT)

        self.outerContentFrame = Frame(root)
        self.outerContentFrame.pack(expand=1, fill=BOTH, padx=10, pady=10)
        
        self.contentCreators = [GeotagSearchContent, DownloadContent, AudioSyncContent, OptimizerContent, ExportContent]
        self.currentContentIndex = -1

        self.contentStack = []
        self.contentFrameStack = []
        self.keyStack = []
        self.infoDict = {}

        self.incrementStack({})

    def setNextButtonUsable(self, value=True):
        self.nextButton["state"] = NORMAL if value else DISABLED

    def setBackButtonUsable(self, value=True):
        self.backButton["state"] = NORMAL if value else DISABLED

    def onBackButton(self):
        self.decrementStack()

    def onNextButton(self):
        self.incrementStack(self.contentStack[-1].getInfoDict())

    def incrementStack(self, infoDict):
        if self.currentContentIndex >= 0:
            self.keyStack.append(list(infoDict.keys()))
            for key in infoDict.keys():
                self.infoDict[key] = infoDict[key]
            self.contentFrameStack[-1].pack_forget()
            self.backButton["state"] = NORMAL

        contentFrame = Frame(self.outerContentFrame)
        contentFrame.pack(expand=1, fill=BOTH)
        self.contentFrameStack.append(contentFrame)
        self.currentContentIndex += 1
        newContent = self.contentCreators[self.currentContentIndex](self, contentFrame)
        self.contentStack.append(newContent)

    def decrementStack(self):
        self.contentStack[-1].destroy()
        self.contentFrameStack[-1].destroy()
        self.contentStack.pop()
        self.contentFrameStack.pop()
        oldKeys = self.keyStack[-1]
        for oldKey in oldKeys:
            del self.infoDict[oldKey]
        self.keyStack.pop()

        self.currentContentIndex -= 1

        self.contentFrameStack[-1].pack(expand=1, fill=BOTH)
        self.contentStack[-1].onSetFocus()
        self.backButton["state"] = DISABLED if self.currentContentIndex == 0 else NORMAL

with tempfile.TemporaryDirectory() as tempdir:
    temp_path = pathlib.Path(tempdir)
    root = Tk()
    root.geometry('800x600')
    window = Window(root, temp_path)
    print(type(temp_path))
    print(type(temp_path / "output.mp4"))
    print(temp_path / "output.mp4")
    root.mainloop()
