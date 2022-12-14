import os, json

import googleapiclient.discovery
import download


def getSearchResponse(searchq, locationString, locationRadiusString, maxresults=25):
    api_service_name = "youtube"
    api_version = "v3"
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
    return matchesRequest(item["snippet"]["title"], searchq)


def matchesRequest(videoTitle, searchq):
    return min(word in videoTitle.lower().split(" ") for word in searchq.lower().split(" "))


def urlsFromSearchWithFilter(func, searchq, locationString, locationRadiusString, maxresults=25):
    r = getSearchResponse(searchq, locationString, locationRadiusString, maxresults)
    results = []
    for item in r["items"]:
        if func(item):
            results.append(item["id"]["videoId"])
    return results



