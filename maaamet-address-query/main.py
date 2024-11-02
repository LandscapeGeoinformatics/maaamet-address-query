from fastapi import FastAPI
import os
import json
import uvicorn as uvicorn

from typing import Optional, Union
from typing import Annotated


from fastapi import FastAPI, Depends, Cookie, Request
from fastapi import Path, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timedelta

import urllib3
from shapely.geometry import box
from shapely.geometry import MultiPolygon, Polygon, shape, mapping
from shapely.ops import transform
from shapely.wkt import loads
import pyproj

from starlette import status

import logging
import logging.config


# create the default logging dictConfig
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',  # Default is stderr
        }
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'gunicorn.access': {
            'handlers': ['console'],
            'level': 'INFO'},
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }

})

try:
    from gunicorn import glogging
    glogging.logconfig_dict = logging.config.dictConfig
except ImportError:
    print("gunicorn not installed, using default logging")

logger = logging.getLogger(__name__)


app = FastAPI()

# Setting up CORS
origins = [
    "http://localhost:8000",
    "http://localhost:5000",
    "http://localhost",
    "https://data-apps.landscape-geoinformatics.org",
    "https://landscape-geoinformatics.ut.ee"
    # add other origins if necessary
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/maaamet-address-search/v1/address")
async def dataquery_address_search(q: str, as_box: int = 0):
    if q is None:
        return HTTPException(detail="No search string q was provided", status_code=400)

    as_point = True
    if int(as_box) == int(1):
        as_point = False
    result = maaamet_address_search(q, as_point)

    if result is None:
        raise HTTPException(status_code=400, detail="search error")

    resp_js = {"message": "OK", "status": 200, "payload" : result}
    return resp_js


def project_geom(geom, from_epsg, to_epsg):
    from_crs = pyproj.CRS(f'EPSG:{from_epsg}')
    to_crs = pyproj.CRS(f'EPSG:{to_epsg}')

    transformer = pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

    est_geom = transform(transformer, geom)
    return est_geom


def maaamet_address_search(s: str, as_point=True):
    http = urllib3.PoolManager()

    resp = http.request(
            "GET",
            "https://inaadress.maaamet.ee/inaadress/gazetteer?",
            fields = {
                "results":10,
                "features":"EHAK,VAIKEKOHT,KATASTRIYKSUS,TANAV,EHITISHOONE",
                "address": s,
                "appartment":0,
                "unik":0,
                "tech":0,
                "iTappAsendus":0,
                "ky":0,
                "poi":0,
                "knr":0,
                "help":0}
            )
    if resp.status != 200:
        raise HTTPException(status_code=resp.status, detail="Maa-amet address search not 200")

    data = json.loads(resp.data.decode('utf-8'))
    # fields = ['pikkaadress', 'taisaadress','viitepunkt_l','viitepunkt_b','g_boundingbox']
    datas = []

    if data is None:
        raise HTTPException(status_code=resp.status, detail="Maa-amet address search is not json")
    elif data.get("addresses", None) is None:
        raise HTTPException(status_code=resp.status, detail="Maa-amet address search doesnt have payload")

    for a in data["addresses"]:
        ft = {
            "type": "Feature",
            "properties": {}
            }
        ft["properties"].update({ "pikkaadress": a["pikkaadress"] })
        ft["properties"].update({ "taisaadress": a["taisaadress"] })

        if as_point is True:
            geometry = {
                    "type": "Point",
                    "coordinates": [ float(a["viitepunkt_l"]), float(a["viitepunkt_b"]) ]
                }
            ft.update({ "geometry": geometry })
        else:
            coords_pairs = [ tuple(map(lambda x: float(x), pair.split(","))) for pair in a["g_boundingbox"].split(" ")]
            geometry = { "type": "Polygon", "coordinates" : [ [ [t[1], t[0]] for t in coords_pairs ] ] }
            ft.update({ "geometry": geometry })

        datas.append(ft)
    return datas


