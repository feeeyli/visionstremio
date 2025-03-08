import datetime

import uvicorn
from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import casefy

from visioncine import catalog_search, get_meta, get_movie_streams, get_series_streams

MANIFEST = {
    "id": "net.feeeyli.visionStremio",
    "version": "0.0.1",

    "name": "Vision Stremio",
    "description": "Assista conteúdos do VisionCine no Stremio!",

    "types": ["movie", "series"],

    "catalogs": [
        {
            "type": "movie",
            "id": "visionstremio",
            "name": "Filmes",
            "extraSupported": ["search"]
        },
        {
            "type": "series",
            "id": "visionstremio",
            "name": "Series",
            "extraSupported": ["search"]
        }
    ],

    "resources": ["catalog", "meta", "stream"],

    "idPrefixes": ["visionstremio", "vsc"]
}


limiter = Limiter(key_func=get_remote_address)
rate_limit = "3/second"


app = FastAPI()


def add_cors(response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.get("/manifest.json")
async def manifest():
    return add_cors(JSONResponse(MANIFEST))


@app.get("/catalog/{type}/visionstremio/search={query}.json")
@limiter.limit(rate_limit)
async def search(type: str, query: str, request: Request):
    catalog = catalog_search(query)
    results = [item for item in catalog if item.get("type") == type] if catalog else []
    return add_cors(JSONResponse(content={"metas": results}))


@app.get("/meta/{type}/{id}.json")
@limiter.limit(rate_limit)
async def meta(type: str, id: str, request: Request):
    # meta_data = next((canal for canal in canais.canais_list(server) if canal["id"] == id), {}) if type == "tv" else {}
    # if meta_data:
    #     meta_data.pop("streams", None)
    meta = get_meta(id)
    return add_cors(JSONResponse(content={"meta": meta}))


@app.get("/stream/{type}/{id}.json")
@limiter.limit(rate_limit)
async def stream(type: str, id: str, request: Request):
    if type == "movie":
        return add_cors(JSONResponse({
            "streams": get_movie_streams(id)
        }))
    elif type == "series":
        return add_cors(JSONResponse({
            "streams": get_series_streams(id)
        }))


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
