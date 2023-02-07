import pathlib
from tkinter import *
from datetime import datetime, timedelta
import webbrowser
import geotagsearch
import tempfile

RESULTS_DISPLAY_LIMIT = 10

class DownloadContent():
    def __init__(self, window, contentFrame):
        self.window = window
        self.contentFrame = contentFrame

        self.downloadingInfoLabel = Label(contentFrame, text="Starting Download...\n\n")
        self.downloadingInfoLabel.pack(anchor="w", expand=1, fill = X)

        self.downloadingInfoLabel

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
        self.window.setNextButtonUsable(len(self.selectedVideos) > 0)

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
        self.window.setNextButtonUsable(True)

    def removeFromSelected(self, selectedVideo):
        self.selectedVideos.remove(selectedVideo)
        selectedVideo.destroy()
        if len(self.selectedVideos) == 0:
            self.window.setNextButtonUsable(False)

    def onRemoveAllButton(self):
        for selectedVideo in list([i for i in self.selectedVideos]):
            self.removeFromSelected(selectedVideo)

    def onFromUrlButton(self):
        url = self.fromUrlEntry.get()
        newSelected = SelectableVideo(self.selectedVideoUrls, url, '"' + url + '"', "x", lambda: 1)
        newSelected.onButtonPress = lambda newSelected=newSelected: self.removeFromSelected(newSelected)
        self.selectedVideos.append(newSelected)
        newSelected.pack()
        self.window.setNextButtonUsable(True)

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
        for selectedVideo in self.selectedVideos:
            urls.append(selectedVideo.url)
        return {"urls": urls}


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
        self.innerFrame.pack(side=TOP, anchor=W, fill=X)
        self.innerLeftFrame.pack(side=LEFT, expand=1, fill=X)
        self.titleText.pack(anchor=W)
        self.urlButton.pack(anchor=W)
        self.rightButton.pack(anchor=E, side=RIGHT, expand=1, fill=Y)

    def onUrlPress(self):
        webbrowser.open(self.url, new=2)

    def destroy(self):
        self.innerFrame.destroy()
        self.innerLeftFrame.destroy()
        self.titleText.destroy()
        self.urlButton.destroy()
        self.rightButton.destroy()




class Window():
    def __init__(self, root, temp_path):
        self.root = root
        self.values = {}
        self.backNextFrame = Frame(root)
        self.backNextFrame.pack()

        self.backButton = Button(self.backNextFrame, text="< Back", command=self.onBackButton)
        self.backButton.pack(side=LEFT)

        self.nextButton = Button(self.backNextFrame, text="Next >", command=self.onNextButton)
        self.nextButton.pack(side=LEFT)

        self.outerContentFrame = Frame(root)
        self.outerContentFrame.pack(expand=1, fill=BOTH, padx=10, pady=10)
        self.contentCreators = [GeotagSearchContent, GeotagSearchContent]
        self.currentContentIndex = -1

        self.contentStack = []
        self.contentFrameStack = []
        self.keyStack = []
        self.infoDict = {}

        self.incrementStack({})

    def setNextButtonUsable(self, value=True):
        self.nextButton["state"] = NORMAL if value else DISABLED

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
