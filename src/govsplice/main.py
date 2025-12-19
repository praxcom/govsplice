# /src/govsplice/main.py
"""This module contains the FastAPI endpoints."""

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

import valhalla

from . import config, data, database
from .types import GeoJSON, JSON, AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create a persistent context across all async FastAPI endpoints."""
    app.state.Debug = config.Debug()
    app.state.Debug.log("main.lifespan, Starting server")

    app.state.topPath = Path(__file__).parent

    app.state.landingPagePath = (
        app.state.topPath / "pages" / "landing.html"
    )
    app.state.viewerPagePath = app.state.topPath / "pages" / "viewer.html"
    app.state.styleSheetPath = (
        app.state.topPath / "pages" / "style_sheet.css"
    )
    if not app.state.Debug.DEBUG_RELOAD_FILES:
        app.state.Debug.log(
            "main.lifespan, DEBUG_RELOAD_FILES==False so loading static files upfront"
        )
        app.state.landingPageHTML = FileResponse(
            path=app.state.landingPagePath, media_type="text/html"
        )
        app.state.viewerPageHTML = FileResponse(
            path=app.state.viewerPagePath, media_type="text/html"
        )
        app.state.globalStyleSheetCSS = FileResponse(
            path=app.state.styleSheetPath, media_type="text/css"
        )

    # TODO: CHANGE THE INITIALISATIONS HERE SO THAT THIS IS PERFORMED THROUGH A DATA ADAPTER, NOT DIRECT USING LSOA METHODS
    # NOR DIRECTLY ACCESSING VALHALLAH!! THE MAIN MODULE SHOULD JUST BE A MESSAGE PASSER WITH A BIT OF LOGIC
    app.state.tilePath = (
        app.state.topPath
        / "data"
        / "tiles"
        / "united-kingdom-latest.osm.pbf.tar"
    )
    if not app.state.tilePath.exists():
        app.state.Debug.log(
            "main.lifespan, Downloading OSM and building valhallah tiles, get read to wait a while!"
        )
        data.PBFTools.get_pbf()
        data.PBFTools.build_valhalla_tar()
        app.state.Debug.log(
            "main.lifespan, Finished building valhallah tiles"
        )
    else:
        app.state.Debug.log("main.lifespan, Valhallah tiles found locally")

    app.state.Debug.log("main.lifespan, Setting Valhalla actor")
    valConfig = valhalla.get_config(
        tile_extract=str(app.state.tilePath),
        tile_dir=str(app.state.tilePath.parent),
        verbose=True,
    )
    app.state.valActor = valhalla.Actor(valConfig)

    app.state.Debug.log("main.lifespan, Starting database")
    app.state.database = database.GovspliceDB(app.state.topPath)
    app.state.database.load_lsoa_geojson()
    app.state.database.load_lsoa_age_bins()

    app.state.Debug.log("main.lifespan, Finished setting up server")

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=FileResponse)
async def landing_page() -> FileResponse:
    """Return the logged-out single page file."""
    if app.state.Debug.DEBUG_RELOAD_FILES:
        app.state.landingPageHTML = FileResponse(
            path=app.state.landingPagePath, media_type="text/html"
        )
    return app.state.landingPageHTML


@app.get("/viewer", response_class=FileResponse)
async def viewer_page() -> FileResponse:
    """Return the logged-in single page file."""
    if app.state.Debug.DEBUG_RELOAD_FILES:
        app.state.viewerPageHTML = FileResponse(
            path=app.state.viewerPagePath, media_type="text/html"
        )
    return app.state.viewerPageHTML


@app.get("/style", response_class=FileResponse)
async def style_sheet() -> FileResponse:
    """Return the global CSS file shared across all files."""
    if app.state.Debug.DEBUG_RELOAD_FILES:
        app.state.globalStyleSheetCSS = FileResponse(
            path=app.state.styleSheetPath, media_type="text/css"
        )
    return app.state.globalStyleSheetCSS


@app.get("/api/v1/isochrone")
async def isochrone(
    eType: str, mode: str, extent: float, lat: float, lon: float
) -> GeoJSON:
    """Get an isochrone or isodistance geoJson boundary.

    Parameters
    ----------
    - eType: Boundary type "time" or "distance".
    - mode: Mode of travel. Must be a Valhalla routing engine keyword.
        e.g. "auto" for car, "pedestrian" for walking, "bicycle" for cycling.
    - extent: The time or distance value for the boundary.
    - lat: Lattitude in degrees of the centre of the search radius.
    - lon: Longitude in degrees of the centre of the search radius.

    Returns
    -------
    - GeoJSON of the isochrone or isodistance boundary. The only feature is a single closed LineString.
        Custom properites used are: "fill-alpha", "fill-colour", "border-alpha", "border-colour".
    """
    query = {
        "locations": [{"lat": lat, "lon": lon}],
        "costing": mode,
        "contours": [{eType: extent}],
    }
    isos = app.state.valActor.isochrone(query)
    isos["features"][0]["properties"] = {
        "fill-alpha": 0.5,
        "fill-colour": "#E60026",
        "border-alpha": 1,
        "border-colour": "#E60026",
    }
    return isos


@app.post("/api/v1/simple_age_bins")
async def simple_age_bins(jsonQuery: Request) -> JSON:
    """Returns counts of male and female (& total) in different age categories for a queried boundary.

    Parameters
    ----------
    - jsonQuery: GeoJSON boundary for a query area.

    Returns
    -------
    - JSON with the field "ageBins" and subfields by gender/age category with values of numerical count
        inside the specified boundary.
    """
    queryArea = await jsonQuery.json()

    # TODO: CHANGE THE CALL HERE SO IT IS TO THE DATABASE ADAPTER NOT DIRECTLY SPECIFYING LSOA
    ageBins = app.state.database.intersect_lsoa_age_bins(queryArea)
    return {"ageBins": ageBins}


# TODO: ADD ENPOINT THAT WILL SET THE USER AGENT TO SOMETHING UNIQUE FOR THE USE OF OSM API
