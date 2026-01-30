#!/bin/bash

echo "Starting FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Wait 3 seconds to make sure FastAPI is ready
sleep 3

echo "Starting Streamlit..."
streamlit run frontend.py --server.port=$PORT --server.address=0.0.0.0


