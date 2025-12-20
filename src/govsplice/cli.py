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
