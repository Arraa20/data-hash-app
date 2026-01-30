#!/bin/bash

echo "Starting FastAPI on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "Starting Streamlit..."
streamlit run frontend.py --server.port=$PORT --server.address=0.0.0.0


