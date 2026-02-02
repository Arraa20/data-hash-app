from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
import csv
import os
import tempfile

app = FastAPI(title="Phone Hashing API")

# Environment variables
API_KEY = os.getenv("API_KEY")
SECRET_SALT = os.getenv("SECRET_SALT", "default_secret_salt")  # fallback for safety

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

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

# ✅ Enterprise-grade salted hashing
def sha256_hash(value: str) -> str:
    salted = f"{value}{SECRET_SALT}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

# Single phone hashing API
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single_phone(phone: str):
    phone = phone.strip()
    if not phone.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number")

    return {"hashed_phone": sha256_hash(phone)}

# CSV hashing API
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
                if "phone" not in columns:
                    raise HTTPException(status_code=400, detail="CSV must contain 'phone' column")

                # ✅ ONLY hashed_phone column
                fieldnames = ["hashed_phone"]
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()

                phone_index = columns.index("phone")
                continue

            # Data rows
            phone = columns[phone_index].strip()

            if phone.isdigit():
                hashed = sha256_hash(phone)
                writer.writerow({"hashed_phone": hashed})

        temp_file.close()

        return FileResponse(
            path=temp_file.name,
            media_type="text/csv",
            filename="anonymized_hashed_output.csv"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
