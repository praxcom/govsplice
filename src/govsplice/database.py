# /src/govsplice/database.py
"""This module contains the adapter interface and implementation of backend database management and querying."""

from pathlib import Path

import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from .types import JSON, GeoJSON


class GovspliceDB:
    """Main container for the state and operations upon the datasets that can be served by the Govsplice application.

    Attributes
    ----------
    - topPath: Usually the path object for the package directory, alternativly the parent directory to the data directory.
    """

    def __init__(self, topPath: Path) -> None:
        """
        Parameters
        ----------
        - topPath: Usually the path object for the package directory, alternativly the parent directory to the data directory.
        """
        self.topPath = topPath

    def load_lsoa_geojson(self) -> None:
        """Load in LSOA boundaries."""
        filePath = self.topPath / "data" / "bounded" / "lsoa_2021.geojson"
        self.lsoaBounds = gpd.GeoDataFrame.from_file(filePath)

    def load_lsoa_age_bins(self) -> None:
        """Load in LSOA age band data."""
        filePath = (
            self.topPath
            / "data"
            / "bounded"
            / "age_bands_lsoa21_year2024.csv"
        )
        self.lsoaAgeBins = gpd.GeoDataFrame.from_file(filePath)

    def intersect_lsoa_age_bins(self, query: GeoJSON) -> JSON:
        """Query a provided boundary for population age bands."""

        queryDF = gpd.GeoDataFrame.from_features(query)
        queryDF.geometry = queryDF.geometry.map(Polygon)
        queryDF.set_crs("EPSG:4326", inplace=True)

        targetCols = [
            "Total",
            "F0-15",
            "F16-29",
            "F30-44",
            "F45-64",
            "F65+",
            "M0-15",
            "M16-29",
            "M30-44",
            "M45-64",
            "M65+",
        ]

        for col in targetCols:
            if col in self.lsoaAgeBins.columns:
                self.lsoaAgeBins[col] = pd.to_numeric(
                    self.lsoaAgeBins[col], errors="coerce"
                ).fillna(0)

        if self.lsoaBounds.crs is None:
            self.lsoaBounds = self.lsoaBounds.set_crs("EPSG:4326")
        if queryDF.crs is None:
            queryDF = queryDF.set_crs("EPSG:4326")

        merged = self.lsoaBounds.merge(self.lsoaAgeBins, on="LSOA21CD")

        targetCRS = "EPSG:27700"
        lsoaProj = merged.to_crs(targetCRS)
        queryProj = queryDF.to_crs(targetCRS)

        lsoaProj["area"] = lsoaProj.geometry.area

        intersection = gpd.overlay(lsoaProj, queryProj, how="intersection")

        intersection["intersection"] = intersection.geometry.area
        intersection["ratio"] = (
            intersection["intersection"] / intersection["area"]
        )

        finalCounts = {}
        for col in targetCols:
            if col in intersection.columns:
                weigtedVals = intersection[col] * intersection["ratio"]
                finalCounts[col] = float(weigtedVals.sum())

        return finalCounts
