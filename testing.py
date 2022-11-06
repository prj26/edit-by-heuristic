import download
import geotagsearch
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
        download.downloadURL(urls[i], "C:\\Users\\User\\Music\\vid" + str(i) + '.%(ext)s')

if __name__ == "__main__":
    urls = filterWembley("foo fighters the pretender")
    print("test complete")

