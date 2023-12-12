#! /bin/bash
set -e
python -m venv .venv
source .venv/bin/activate
which python
python -m pip install -r ./requirements.txt