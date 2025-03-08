import re

import requests
import casefy
from bs4 import BeautifulSoup


SEASON_IMAGES = [
    "https://imgur.com/tpHm1EB.png",
    "https://imgur.com/1fCkobE.png",
    "https://imgur.com/9gxVSAB.png",
    "https://imgur.com/kxiCvtE.png",
    "https://imgur.com/LTx2itX.png",
    "https://imgur.com/BOF4Tjn.png",
    "https://imgur.com/cRGSl6u.png",
    "https://imgur.com/dqlWwFH.png",
    "https://imgur.com/FM6EMyO.png",
    "https://imgur.com/TxDHzLS.png",
    "https://imgur.com/V44FzrN.png",
    "https://imgur.com/5JjRDtB.png",
    "https://imgur.com/JEQiTJF.png",
    "https://imgur.com/MGtBCAk.png",
    "https://imgur.com/OzbWtdB.png",
    "https://imgur.com/5AFHxwk.png"
]


def get_poster_url(text):
    result = re.search(r"url\((.+)\)", text)
    return result.group(1).replace("'", "")


def catalog_search(q: str):
    search_url = f"https://www.visioncine-1.com/search.php?q={q}"

    r = requests.get(search_url)

    soup = BeautifulSoup(r.text, "html.parser")

    elements = soup.select(".item.poster")

    catalog = []

    for element in elements:
        url_id = element.select_one(".info.movie .buttons a:has(.far.fa-play)")["href"].split("watch/")[1]
        title = element.select_one(".info.movie h6").text
        tags = element.select(".info.movie .tags span")
        tp = "series" if "Temporada" in tags[0].text else "movie"
        year = tags[1].text

        catalog.append({
            "id": f"vsc{casefy.pascalcase(url_id)}",
            "type": tp,
            "title": title,
            "year": int(year),
            "poster": get_poster_url(element.select_one(".content")["style"])
        })

    return catalog


def get_meta(id: str):
    url = f"https://www.visioncine-1.com/watch/{casefy.kebabcase(id.replace("vsc", "", 1))}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    poster = get_poster_url(soup.select_one(".infoPoster .watching .poster")["style"])
    type = "series" if "Temporada" in soup.select_one(".infoPoster .info .log").text else "movie"
    name = soup.select_one(".infoPoster .info h1").text
    genres = soup.select(".producerInfo p span span")
    background = get_poster_url(soup.select_one(".backImage")["style"])

    seasons = list(map(lambda x: x["value"], soup.select(".seasons #seasons-view option")))

    meta = {
        "id": id,
        "type": type,
        "name": name,
        "genres": sorted(list(map(lambda x: x.text, genres))),
        "poster": poster,
        "background": background
    }

    if type == "series":
        meta["videos"] = get_series_episodes(id, seasons)
    elif type == "movie":
        meta["behaviorHints"] = {
            "defaultVideoId": id,
            "hasScheduledVideos": False,
        }

    return meta


def get_series_episodes(id: str, seasons: list[str]):
    result = []

    for i, season in enumerate(seasons):
        url = f"https://www.visioncine.stream/ajax/episodes.php?season={season}"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        episodes = soup.select(".ep")

        thumbnail = SEASON_IMAGES[i] if i <= 14 else SEASON_IMAGES[15]

        for episode in episodes:
            ep_number = episode.select_one("& > p").text

            result.append({
                "id": f"{id}:{i + 1}:{ep_number}",
                "title": f"Episódio {ep_number}",
                "thumbnail": thumbnail,
                "released": "2025-01-01",
                "season": i + 1,
                "episode": ep_number
            })
        #
        # for episode in episodes:
        #     watch_url = episode.select_one('.mobile .buttons a[data-tippy-content^="Assistir"]')["href"]


    return result


def get_movie_streams(id: str):
    movie_page_url = f"https://www.visioncine-1.com/watch/{casefy.kebabcase(id.replace("vsc", "", 1))}"
    r = requests.get(movie_page_url)
    soup = BeautifulSoup(r.text, "html.parser")

    watch_button_url = soup.select_one('.infoPoster [data-tippy-content^="Assistir"]')["href"]

    return get_all_video_urls(watch_button_url)


def get_series_streams(id: str):
    split = id.split(":")
    season = int(split[1])
    episode = int(split[2])

    season_id = get_season_id(split[0], season)

    url = f"https://www.visioncine.stream/ajax/episodes.php?season={season_id}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    return get_all_video_urls(soup.select('.mobile .buttons a[data-tippy-content^="Assistir"]')[episode - 1]["href"])



def get_season_id(id: str, season: int):
    url = f"https://www.visioncine-1.com/watch/{casefy.kebabcase(id.replace("vsc", "", 1))}"

    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # seasons = list(map(lambda x: x["value"], ))

    return soup.select_one(f".seasons #seasons-view option:nth-child({season})")["value"]


def get_all_video_urls(default_url: str):
    r = requests.get(default_url)
    default_page_soup = BeautifulSoup(r.text, "html.parser")

    pages_links = default_page_soup.select("footer .dropdown-menu.dropdown-menu-right .dropdown-item.source-btn")

    result = [{
        "name": "Vision Stremio",
        "description": pages_links[0].text.split("Multi")[0],
        "url": get_video_url(r.text)
    }]

    if len(pages_links) > 1:
        for page in pages_links[1:]:
            if "Premium" not in page.text:
                spr = requests.get(page["href"])

                result.append({
                    "name": "Vision Stremio",
                    "description": page.text.split("Multi")[0],
                    "url": get_video_url(spr.text)
                })

    return result


def get_video_url(text: str):
    mp4_result = re.search(r"initializePlayer\('(.+)\.mp4'", text)
    m3u8_result = re.search(r"initializePlayer\('(.+)\.m3u8'", text)

    if mp4_result:
        return f"{mp4_result.group(1)}.mp4"
    elif m3u8_result:
        return f"{m3u8_result.group(1)}.m3u8"
    else:
        return ""
