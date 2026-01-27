from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import pandas as pd
import os

app = FastAPI(title="Phone Hashing API")

# Read from Railway env variables
API_KEY = os.getenv("API_KEY")
SECRET_SALT = os.getenv("SECRET_SALT")

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=True
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

    hashed_phone = sha256_hash(phone)
    return {"hashed_phone": hashed_phone}

@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
def hash_csv(file_path: str = Query(..., description="Path to CSV with 'phone' column")):
    try:
        df = pd.read_csv(file_path)

        if "phone" not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must have 'phone' column")

        df["hashed_phone"] = df["phone"].astype(str).apply(sha256_hash)
        output_path = "hashed_output.csv"
        df.to_csv(output_path, index=False)

        return {"message": f"Hashed CSV saved as {output_path}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
