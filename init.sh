#!/bin/bash
source /opt/conda/bin/conda init bash
source /opt/conda/bin/activate govsplice

python src/govsplice/data.py
govsplice