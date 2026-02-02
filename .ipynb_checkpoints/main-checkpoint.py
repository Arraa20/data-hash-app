from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
import csv
import os
import tempfile
import re

app = FastAPI(title="Meta-Friendly Phone Hashing API")

# Environment variables
API_KEY = os.getenv("API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# Meta-compatible SHA-256 hash (no salt)
def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# Canonical phone normalization for Meta
def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)  # remove non-digits
    if digits.startswith("0"):
        digits = "94" + digits[1:]      # 0xxxx → 94xxxx
    elif digits.startswith("7"):
        digits = "94" + digits          # 7xxxx → 947xxxx
    return digits

# Single phone hashing endpoint
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single_phone(phone: str):
    normalized = normalize_phone(phone.strip())
    if not normalized.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number")
    return {"hashed_phone": sha256_hash(normalized)}

# CSV hashing endpoint (any first column)
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
        writer = None

        for line in file.file:
            decoded_line = line.decode("utf-8").strip()
            if not decoded_line:
                continue

            columns = decoded_line.split(",")

            # Header row
            if writer is None:
                target_index = 0  # hash the first column
                writer = csv.DictWriter(temp_file, fieldnames=["hashed_phone"])
                writer.writeheader()
                continue

            raw_value = columns[target_index].strip()
            normalized = normalize_phone(raw_value)
            if not normalized:
                continue

            hashed = sha256_hash(normalized)
            writer.writerow({"hashed_phone": hashed})

        temp_file.close()

        return FileResponse(
            path=temp_file.name,
            media_type="text/csv",
            filename="hashed_output.csv"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
