from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
#import pandas as pd
import os
import csv
import hashlib

app = FastAPI(title="Phone Hashing API")

# Railway environment variables
API_KEY = os.getenv("API_KEY")
SECRET_SALT = os.getenv("SECRET_SALT")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# Enable CORS for frontend service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def sha256_hash(value: str) -> str:
    return hashlib.sha256((value + SECRET_SALT).encode("utf-8")).hexdigest()

@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single_phone(phone: str):
    phone = phone.strip()
    if not phone.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number")
    return {"hashed_phone": sha256_hash(phone)}

@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
import csv
import hashlib

def hash_csv_file(input_file, output_file, salt):
    with open(input_file, newline='') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=["phone", "hashed_phone"])
        writer.writeheader()
        for row in reader:
            phone = row["phone"]
            hashed = hashlib.sha256((phone + salt).encode()).hexdigest()
            writer.writerow({"phone": phone, "hashed_phone": hashed})

# Optional debug route
@app.get("/debug")
def debug():
    return {"API_KEY_loaded": API_KEY is not None, "SECRET_SALT_loaded": SECRET_SALT is not None}
