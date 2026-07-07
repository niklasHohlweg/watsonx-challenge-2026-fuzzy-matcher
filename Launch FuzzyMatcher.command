#!/bin/bash
# FuzzyMatcher launcher for macOS
# Double-click this file in Finder to start the application.
# (If macOS asks "Are you sure?", click Open.)

# Navigate to the directory containing this script
cd "$(dirname "$0")"

# Activate the virtual environment and launch
source .venv/bin/activate
python main.py
