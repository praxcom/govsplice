# /src/govsplice/config.py
"""This module contains global configs & config helpers."""

from datetime import datetime

from pathlib import Path

from govsplice import data

class Debug:
    """Container for configs that impact debug behaviour.

    Class Attributes
    ----------------
    - DEBUG_PRINT_MESSAGES: When true, log messages are printed to console.
    - DEBUG_RELOAD_FILES: When ture, browser files will reload for each relevant query.
    - DEBUG_SECURITY: When true, there will be less caution in protecting internal states from client view.
    - DEBUG_LOG_FILE: When a valid file path, log messages are saved here. File does not have to exist.
    """

    DEBUG_PRINT_MESSAGES: bool = True
    DEBUG_RELOAD_FILES: bool = True
    DEBUG_SECURITY: bool = True
    DEBUG_LOG_FILE: Path | None = None

    @classmethod
    def log(cls, message: str) -> None:
        """Log custom message to console and/or a file.

        Parameters
        ----------
        - messages: The message to log according to the rules controled by class attributes.
        """
        now = datetime.now()
        m = f"[{now.strftime('%Y/%m/%d %H:%M:%S')}][govsplice]: {message}"
        if cls.DEBUG_PRINT_MESSAGES:
            print(m)
        if cls.DEBUG_LOG_FILE:
            cls.DEBUG_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with cls.DEBUG_LOG_FILE.open(mode="a", encoding="utf-8") as f:
                f.write("\n" + m)


def build_valhala_config() -> None:
    """Create the JSON config file required for building tiles for the Valhalla routing engine."""
    dataDir = Path(__file__).parent / "data"
    tileDir = dataDir / "tiles"
    configTemplatePath = dataDir / "config" / "template_valhalla.json"
    configPath = dataDir / "config" / "valhalla.json"

    with open(configTemplatePath, "r") as f:
        template = f.read()
    with open(configPath, "w") as f:
        f.write(template.replace("$VALPATH", str(tileDir)))


DATASET_MAPPINGS = {
    "simple_age_bins":data.Stat_AgeGenderBands2021
}

DOCS_OPEN_ACCESS = None #"/docs"

SECRET_KEY = "341965d7fde165fa036f6d5f47295ec2da7822d1b1726b5ceb8a860e765223ef"#CHANGE ME!!!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ADMIN_ACCOUNT = {
    "name" : "",
    "username" : "admin", #Must be the same as the key in the top level dict
    "hashPass":"$2b$12$Kgar3I37N9zxfkDnlHoQ4eUNIRDygrfbOAwEtuz9DFOg92XUowASu", #"admin"
    "subscribed": True
}

ASSET_MAP = {
    "demo-img-1":Path(__file__).parent / "pages" / "assets" / "demo-img-1.png",
}