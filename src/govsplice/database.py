# /src/govsplice/database.py
"""This module contains the adapter interface and implementation of backend database management and querying."""

from pathlib import Path

import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from govsplice.local_types import JSON, GeoJSON
from govsplice import data, config

class DataBase:
    """Main container for the state and operations upon the datasets that can be served by the Govsplice application.

    Serves as the abstraction layer between the web endpoints and the actual analyses that need to be done.

    Attributes
    ----------
    - topPath: Usually the path object for the package directory, alternativley the parent directory to the data directory.
    """

    def __init__(self, topPath: Path) -> None:
        """
        Parameters
        ----------
        - topPath: Usually the path object for the package directory, alternativly the parent directory to the data directory.
        - dataSources: A dictionary of the dataset mapping keywords to initialised objects of data sources.
        """
        self.topPath = topPath
        self.dataSources = {}
        for dataset in config.DATASET_MAPPINGS:
            self.dataSources[dataset] = config.DATASET_MAPPINGS[dataset]()
            self.dataSources[dataset]._setup_data()

    def area_stats(self, queryArea: GeoJSON, dataset: str) -> JSON:
        """Query a metric over one or more geospatial boundaries.

        Parameters
        ----------
        - queryArea: One spatial boundary to return statisics with.
        - dataset: The keyword for the statistic being requested.

        Returns
        -------
        - JSON object containing the data for the region queries. Structure depends on the metric requested.
        """
        return self.dataSources[dataset].intersection(queryArea)