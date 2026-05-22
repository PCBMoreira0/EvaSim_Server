#!/bin/bash

cd /app/server
uvicorn main:app --host 0.0.0.0 --port 8000 &

cd /app/sim/evaml_2025_server
python teste1.py