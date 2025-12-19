# src/govsplice/data.py
"""This module downloads, extracts, transforms and saves datasets to the server instance."""

from pathlib import Path
import subprocess
import sys

import wget

from . import config


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
