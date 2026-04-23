#!/bin/sh
cd /app
export PYTHONPATH=/app:$PYTHONPATH
python whale_tracker/whale_api.py &
python whale_tracker/main.py &
wait
