import os
import datetime

import googleapiclient.discovery
import googlemaps

gmaps = googlemaps.Client(key=os.getenv("MAPSAPIKEY"))

def geocode(string):
    # just an API call
    return gmaps.geocode(string)

def coordsFromGeocodeResult(result):
    # interprets the result of calling the gmaps library, extracting location
    location = result["geometry"]["location"]
    return location["lat"], location["lng"]

def getSearchResponse(searchq, locationString, locationRadiusString, maxresults=25):
    # API call to the Youtube API, using the recommended implementation
    api_service_name = "youtube"
    api_version = "v3"

    # API key is stored in the environment variables,
    # so the code can be published without leaking the key
    DEVELOPER_KEY = os.getenv("YOUTUBEAPIKEY")

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)

    request = youtube.search().list(
        part="snippet",
        maxResults=maxresults,
        q=searchq,
        type="video",
        location=locationString,
        locationRadius=locationRadiusString
    )
    response = request.execute()

    return response

def filterByVideoTitle(item, searchq):
    # wrapper over matchesRequest so it fits the format the urlsAndItemsFromSearchWithFilter uses
    return matchesRequest(item["snippet"]["title"], searchq)

def filterByDate(item, searchq, firstDatetime, secondDatetime):
    # checks that a video is between two datetimes
    return firstDatetime <= ytStringToDatetime(item["snippet"]["publishedAt"]) < secondDatetime

def filterByTitleAndDate(item, searchq, firstDatetime, secondDatetime):
    # combines filterByVideoTitles and filterByDate into a single function
    return filterByVideoTitle(item, searchq) and filterByDate(item, searchq, firstDatetime, secondDatetime)

def matchesRequest(videoTitle, searchq):
    # checks that a video title actually contains all of the words the user entered
    # (this is not guaranteed by Youtube)
    return min(word in [titleword.strip("'\",") for titleword in videoTitle.lower().split(" ")] for word in searchq.lower().split(" "))

def ytStringToDatetime(string):
    #converts the upload date string that Youtube returns into a python datetime object
    return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%SZ")

def urlsAndItemsFromSearchWithFilter(func, searchq, locationString, locationRadiusString, maxresults=25):
    # wrapper over getSearchResponse that filters the results using the provided function func
    r = getSearchResponse(searchq, locationString, locationRadiusString, maxresults)
    results = []
    items = []
    for item in r["items"]:
        if func(item):
            results.append(item["id"]["videoId"])
            items.append(item)
    return results, items




