#!/usr/bin/env bash
python3 -m get-pip.py
pip install virtualenv
virtualenv env -p python3
source env/bin/activate
pip install -U -r requirements.txt
deactivate