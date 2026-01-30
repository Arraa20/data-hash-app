from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
import csv
import os
import tempfile

app = FastAPI(title="Phone Hashing API")

# Railway environment variables
API_KEY = os.getenv("API_KEY")
SECRET_SALT = os.getenv("SECRET_SALT")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with frontend URL for security
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
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    try:
        # Create a temporary output file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        output_path = temp_file.name

        # Read input CSV and write hashed CSV
        input_content = file.file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(input_content)
        if "phone" not in reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV must contain 'phone' column")

        writer = csv.DictWriter(temp_file, fieldnames=["phone", "hashed_phone"])
        writer.writeheader()

        for row in reader:
            phone = row["phone"].strip()
            hashed = sha256_hash(phone)
            writer.writerow({"phone": phone, "hashed_phone": hashed})

        temp_file.close()

        return FileResponse(path=output_path, media_type="text/csv", filename="hashed_output.csv")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
