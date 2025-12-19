# /src/govsplice/cli.py
"""This module implments the command line interface endpoints."""

import uvicorn

def run() -> None:
    """Run the Govsplice server"""
    uvicorn.run(
        "govsplice.main:app",  
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

#TODO: ADD MORE CLI TOOLS FOR SETTING UP DATA SOURCES AND MAKING SURE ALL THE REQUIRMENTS ARE IN PLACE