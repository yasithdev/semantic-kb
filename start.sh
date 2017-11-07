#!/usr/bin/env bash

# Switch to current directory
cd "${0%/*}"

echo "Activating virtual environment"
source env/bin/activate
echo "Starting Semantic KB"
nohup python app.py > app.log 2> app.err < /dev/null &
echo "Semantic KB started. Deactivating virtual environment..."
deactivate