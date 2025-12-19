#TODO: CLEAN UP THE COMMENTING AND DOCSTRINGS FOR THIS MODULE
#TODO: MAKE SURE THE PATHS BEING REFERENCED FOLLOW THE NEW PACKAGE STRUCTURE
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
        self.topPath = topPath

    def load_lsoa_geojson(self):
        filePath = self.topPath / "data" / "bounded" / "lsoa_2021.geojson"
        self.lsoaBounds = gpd.GeoDataFrame.from_file(filePath)
    
    def load_lsoa_age_bins(self):
        filePath = self.topPath / "data" / "bounded" / "age_bands_lsoa21_year2024.csv"
        self.lsoaAgeBins = gpd.GeoDataFrame.from_file(filePath)

    def intersect_lsoa_age_bins(self, query):        
            queryDF = gpd.GeoDataFrame.from_features(query)
            # Note: Depending on your shapely version, .map(Polygon) might be redundant 
            # if from_features already created geometry objects, but keeping as requested.
            queryDF.geometry = queryDF.geometry.map(Polygon)
            queryDF.set_crs("EPSG:4326", inplace=True)

            # --- 1. DEFINE TARGET COLUMNS ---
            target_cols = [
                'Total', 
                'F0-15', 'F16-29', 'F30-44', 'F45-64', 'F65+',
                'M0-15', 'M16-29', 'M30-44', 'M45-64', 'M65+'
            ]

            # --- 2. CLEAN DATA TYPES ---
            # We iterate through the columns and force them to numeric types.
            # errors='coerce' turns bad data (like empty strings) into NaN.
            # .fillna(0) turns those NaNs into 0.0 so math works.
            for col in target_cols:
                if col in self.lsoaAgeBins.columns:
                    self.lsoaAgeBins[col] = pd.to_numeric(
                        self.lsoaAgeBins[col], 
                        errors='coerce'
                    ).fillna(0)
                else:
                    pass
                    #print(f"Warning: {col} not found in lsoaAgeBins source data")

            if self.lsoaBounds.crs is None:
                self.lsoaBounds = self.lsoaBounds.set_crs("EPSG:4326")
            if queryDF.crs is None:
                queryDF = queryDF.set_crs("EPSG:4326")

            #print(f"LSOA Bounds Rows: {len(self.lsoaBounds)}")
            #print(f"Age Bins Rows: {len(self.lsoaAgeBins)}")

            merged = self.lsoaBounds.merge(self.lsoaAgeBins, on="LSOA21CD")
            #print(f"Merged Rows: {len(merged)}")
            
            # if len(merged) == 0:
            #     print(f"Bounds Key Example: '{self.lsoaBounds['LSOA21CD'].iloc[0]}'")
            #     print(f"Bins Key Example:   '{self.lsoaAgeBins['LSOA21CD'].iloc[0]}'")

            targetCRS = "EPSG:27700"
            lsoaProj = merged.to_crs(targetCRS)
            queryProj = queryDF.to_crs(targetCRS)

            # print(f"LSOA Bounds (BNG): {lsoaProj.total_bounds}")
            # print(f"Query Bounds (BNG): {queryProj.total_bounds}")

            lsoaProj["area"] = lsoaProj.geometry.area

            intersection = gpd.overlay(lsoaProj, queryProj, how="intersection")
            #print(f"Intersection Fragments: {len(intersection)}")

            intersection["intersection"] = intersection.geometry.area
            intersection["ratio"] = intersection["intersection"] / intersection["area"]

            # --- 3. CALCULATE WEIGHTED SUMS ---
            final_counts = {}

            # We now loop specifically over the target columns
            for col in target_cols:
                if col in intersection.columns:
                    # Multiply the population column by the intersection ratio
                    weighted_values = intersection[col] * intersection["ratio"]
                    final_counts[col] = float(weighted_values.sum())
            
            return final_counts #dict of each category

# #TODO: CREATE THE QUERY ADAPTER TO ALL OF THE USES OF THE DATABASE ---> MAYBE DO SOME RESEARCH ON THE WRITE PATTERN TO DO THIS TO MAINTAIN GOOD ABSTRACTION?
# class QueryAdapter:
#     """Collection of static methods for abstracting queries away from the specific data fetching methods."""
#     @staticmethod
#     def grouped_age_gender_count(boundary: GeoJSON) -> JSON:
#         pass
    