# src/govsplice/data.py
"""This module downloads, extracts, transforms and saves datasets to the server instance."""

from pathlib import Path
import subprocess
import sys
import requests
import json

import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

import wget

from govsplice import config
from govsplice.local_types import JSON, GeoJSON


class PBFTools:
    """A collection of static methods for using open street map .pbg files."""

    @staticmethod
    def get_pbf(
        url: str = "https://download.geofabrik.de/europe/united-kingdom-latest.osm.pbf",
        saveAs: str | None = None,
    ) -> None:
        """Download an open street maps pbf.

        Parameters
        ----------
        - url: Full url to the .pbf file of interest. Defaults to UK as this is the current focus of Govsplice.
        - saveAs: Provides the option to save somewhere other than the govsplice directory
            or add modified version naming to the file, for example.
        """
        if not saveAs:
            saveAs = (
                Path(__file__).parent
                / "data"
                / "tiles"
                / "united-kingdom-latest.osm.pbf"
            )
        config.Debug.log(f"data.PBFTools.get_pbf, Trying wget {url}")
        wget.download(url, out=str(saveAs), bar=wget.bar_thermometer)
        config.Debug.log(f"data.PBFTools.get_pbf, Success wget {url}")

    @staticmethod
    def build_valhalla_tar(
        configPath: str | None = None, pbfPath: str | None = None
    ) -> None:
        """Build tiles for Valhalla routing engine, and compress to tar.

        Parameters
        ----------
        - configPath: Path for the JSON config file needed during building of tiles.
        - pbfPath: Path for the open street maps tiles download.
        """
        dataPath = Path(__file__).parent / "data"
        if not configPath:
            configPath = dataPath / "config" / "valhalla.json"
        if not pbfPath:
            pbfPath = dataPath / "tiles" / "united-kingdom-latest.osm.pbf"

        config.build_valhala_config()
        config.Debug.log(
            "data.PBFTools.build_valhallah_tar, Built Valhalla config"
        )

        cmd = [
            sys.executable,
            "-m",
            "valhalla",
            "valhalla_build_admins",
            "-c",
            str(configPath),
            str(pbfPath),
        ]
        subprocess.run(cmd, check=True)
        config.Debug.log(
            "data.PBFTools.build_valhallah_tar, Built Valhalla admins"
        )

        cmd = [
            sys.executable,
            "-m",
            "valhalla",
            "valhalla_build_tiles",
            "-c",
            str(configPath),
            str(pbfPath),
        ]
        subprocess.run(cmd, check=True)
        config.Debug.log(
            "data.PBFTools.build_valhallah_tar, Built Valhalla tiles"
        )

        cmd = ["tar", "-cvf", str(pbfPath) + ".tar", str(pbfPath)]
        subprocess.run(cmd, check=True)
        config.Debug.log(
            "data.PBFTools.build_valhallah_tar, Compressed Valhalla tiles to tar"
        )

class Base_BoundedStatistic:
    """Base class for statistical sources that are associated with a spatial boundary.

    Class Attributes
    ----------------
    - boundaryURL: Source URL for the statistical boundary.
    - boundaryFilePath: Path to save the downloaded boundaries.
    - statsURL: Source URL for statistical data linked to the boundary.
    - statsFilePath: Path to save the downloaded stats.
    - key: The field name that links the stats and boundaries.
    - targetCols: Columns of the stats that should have an intersection calculated over them.

    Attributes
    ----------
    - rawStats: Geodataframe of loaded statistical table.
    - rawBounds: Geodataframe of loaded spatial boundaries.
    - data: Joined dataset of the boundaries and statistical data.
    """
    boundaryURL: str | None = None
    boundaryFilePath: Path | None = None
    statsURL: str | None = None
    statsFilePath: Path | None = None
    key: str | None = None
    targetCols: list[str] | None = None

    def __init__(self) -> None:
        self.rawStats: gpd.GeoDataFrame | None  = None
        self.rawBounds: gpd.GeoDataFrame | None = None
        self.data: gpd.GeoDataFrame | None = None
        if not all([self.boundaryURL,
                   self.boundaryFilePath,
                   self.statsURL,
                   self.statsFilePath,
                   self.key,
                   self.targetCols]):
            raise AttributeError("The subclass of BoundedStatistic has not set all required class attributes.")
    
    def load_boundaries(self) -> None:
        raise NotImplementedError

    def load_stats(self) -> None:
        raise NotImplementedError
    
    def download_boundaries(self) -> None:
        raise NotImplementedError
    
    def download_stats(self) -> None:
        raise NotImplementedError
    
    def _join_geojson(self, jsonList: list[GeoJSON]) -> GeoJSON:
        """Join a list of GeoJson feature collections into one.

        Parameters
        ----------
        - jsonList: A list of GeoJson feature collections.

        Returns
        -------
        - A GeoJSON as a dict.
        """
        config.Debug.log("data.Base_BoundedStatistic._join_geojson, Processing GeoJson")
        uniqueFeatures = []
        seenIds = []
        for json in jsonList:
            for f in json["features"]:
                id = f["id"]
                if id not in seenIds:
                    uniqueFeatures.append(f)                    
                seenIds.append(id)
        
        return {"type":"FeatureCollection",
                "crs":{"type":"name","properties":{"name":"EPSG:4326"}},
                "features":uniqueFeatures,
        }

    def _geoportal_pagination_request(self, offsetBy: int) -> list[GeoJSON]:
        """Make multiple requests due to limited row response for uk geoportal data source.

        Assumes 'resultOffset' query field is the last in the url.

        Parameters
        ----------
        - offsetBy: How many rows to offset for each fresh request.

        Returns
        -------
        - A list of GeoJSON feature collections as dicts.
        """
        config.Debug.log("data.Base_BoundedStatistic._geoportal_pagination_request, Downloading multi-page GeoJson")
        join = []
        offset = 0
        moreData = True
        while moreData:
            response = requests.get(self.boundaryURL+str(offset))
            response.raise_for_status()
            newData = response.json()

            join.append(newData)

            if "properties" not in newData:
                newData["properties"] = {}

            if "exceededTransferLimit" in newData["properties"]:
                moreData = newData["properties"]["exceededTransferLimit"]
            else:
                moreData = False

            offset += offsetBy
        
        return join

    
    def _setup_data(self) -> None:
        """Initialise each of the components of the dataset if not already manually done."""
        if self.rawStats is None:
            self.load_stats()
            
        if self.rawBounds is None:
            self.load_boundaries()
            if self.rawBounds.crs is None:
                self.rawBounds.set_crs("EPSG:4326", inplace=True)

        if self.data is None:
            self.data = self.rawBounds.merge(self.rawStats, on=self.key)
            self.data = self.data.to_crs("EPSG:27700")
            self.data["area"] = self.data.geometry.area
    
    def intersection(self, queryBoundary: GeoJSON) -> JSON:
        """Calculate the intersection of a query boundary over the top of the bounded statistics.

        Parameters
        ----------
        - queryBoundary: A closed boundary isochrone/isodistance to query over the base dataset.

        Returns
        -------
        - The weighted intersection of the bounded datasets's target columns.
        """
        self._setup_data()
        queryBoundary = gpd.GeoDataFrame.from_features(queryBoundary)
        queryBoundary.geometry = queryBoundary.geometry.map(Polygon)
        queryBoundary.set_crs("EPSG:4326", inplace=True)
        queryBoundary = queryBoundary.to_crs("EPSG:27700")

        for col in self.targetCols:
            self.data[col] = pd.to_numeric(
                self.data[col], 
                errors='coerce'
                ).fillna(0)

        intersect = gpd.overlay(self.data, queryBoundary, how="intersection")
        intersect["intersection"] = intersect.geometry.area
        intersect["ratio"] = intersect["intersection"] / intersect["area"]
    
        finalCounts = {}
        for col in self.targetCols:
            if col in intersect.columns:
                weigtedVals = intersect[col] * intersect["ratio"]
                finalCounts[col] = float(weigtedVals.sum())

        return finalCounts
    

class Boundary_LSOACensus2021(Base_BoundedStatistic):
    """Subclass for LSOA boundaries used in the UK 2021 census."""
    boundaryURL: str = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BSC_V4/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson&crs=EPSG:4326&resultOffset="
    boundaryFilePath: Path = Path(__file__).parent / "data" / "bounded" / "Boundary_LSOACensus2021.geojson"
    key: str = "LSOA21CD"

    def download_boundaries(self) -> None:
        """Download the LSOA 2021 boundaries for UK ONS geoportal."""
        config.Debug.log("data.Boundary_LSOACensus2021.download_boundaries, Downloading LSOA bounds")
        raw = self._geoportal_pagination_request(1998)
        joined = self._join_geojson(raw)
        with open(self.boundaryFilePath, 'w') as f:
            json.dump(joined, f, indent=4)
            #f.write(str(joined))
        config.Debug.log("data.Boundary_LSOACensus2021.download_boundaries, LSOA bounds saved to local")
        
    def load_boundaries(self):
        """Load the LSOA 2021 boundaries into a GeoDataFrame."""
        config.Debug.log("data.Stat_AgeGenderBands2021.load_stats, Loading local boundaries for 2021 LSOA bounds.")
        self.rawBounds = gpd.GeoDataFrame.from_file(self.boundaryFilePath)
        

class Stat_AgeGenderBands2021(Boundary_LSOACensus2021):
    """Subclass for the mid-2024 age bands by gender estimates on LSOA 2021 census boundaries."""
    statsURL: str = "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/lowersuperoutputareamidyearpopulationestimatesnationalstatistics/mid2022revisednov2025tomid2024/sapelsoabroadage20222024.xlsx"
    statsFilePath: Path = Path(__file__).parent / "data" / "bounded" / "Stat_AgeGenderBands2021.csv"
    targetCols: list[str] = ["F0-15", "F16-29", "F30-44", "F45-64", "F65+", "M0-15", "M16-29", "M30-44", "M45-64", "M65+"]

    def download_stats(self) -> None:
        """Download the 2021 census age bands to a local csv."""
        config.Debug.log("data.Stat_AgeGenderBands2021.download_stats, Dowloading 2024 Age by gender bands for 2021 LSOA bounds")
        tempPath = str(self.statsFilePath)+"_TEMP"
        #wget.download(self.statsURL, out=tempPath, bar=wget.bar_thermometer)
        response = requests.get(self.statsURL)
        response.raise_for_status()
        with open(tempPath, "wb") as f:
            f.write(response.content)
        spreadSheet = pd.read_excel(tempPath,
                                    sheet_name="Mid-2024 LSOA 2021",
                                    header=3)
        spreadSheet.rename(columns={
            "LSOA 2021 Code":self.key,
            "F0 to 15": "F0-15",
            "F16 to 29": "F16-29",
            "F30 to 44": "F30-44",
            "F45 to 64": "F45-64",
            "F65 and over": "F65+",
            "M0 to 15": "M0-15",
            "M16 to 29": "M16-29",
            "M30 to 44": "M30-44",
            "M45 to 64": "M45-64",
            "M65 and over": "M65+",
        }, inplace=True)
        spreadSheet.to_csv(self.statsFilePath, index=False)
        config.Debug.log("data.Stat_AgeGenderBands2021.download_stats, Competed download 2024 Age by gender bands for 2021 LSOA bounds.")
    
    def load_stats(self) -> None:
        """Load the 2021 census age bands to a local csv to a GeoDataFrame"""
        config.Debug.log("data.Stat_AgeGenderBands2021.load_stats, Loading local stats for 2024 Age by gender bands for 2021 LSOA bounds.")
        self.rawStats = gpd.GeoDataFrame.from_file(self.statsFilePath)



if __name__ == "__main__":
    a = Stat_AgeGenderBands2021()
    a.download_stats()
    a.download_download_boundaries()
    print("DONWLOADED")