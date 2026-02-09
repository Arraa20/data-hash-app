import hashlib
import csv
import os
import tempfile
import re
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from urllib.parse import quote

app = FastAPI(title="Meta Phone & Email Hashing API")

# --- CONFIGURATION ---
API_KEY = os.getenv("API_KEY", "your-default-key-for-testing")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UTILITIES ---

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

def normalize_phone(phone: str) -> str:
    """Normalize phone to E.164 format (specifically for LK +94)"""
    phone = re.sub(r"\D", "", str(phone))
    if not phone:
        return ""
    # Handle local leading 0 (e.g., 077...)
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    # Handle missing country code (e.g., 77...)
    elif phone.startswith("7") and len(phone) == 9:
        phone = "94" + phone
    return phone

def normalize_email(email: str) -> str:
    return email.strip().lower()

def sha256_hash(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def sanitize_filename(name: str) -> str:
    # Get filename without extension
    base_name = os.path.splitext(name)[0]
    return re.sub(r"[^\w\d-]", "_", base_name)

def remove_file(path: str):
    """Background task to delete temp file after response is sent"""
    try:
        os.unlink(path)
    except Exception:
        pass

# --- ENDPOINTS ---

@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single(phone: str):
    normalized = normalize_phone(phone)
    return {"original": phone, "normalized": normalized, "hashed": sha256_hash(normalized)}

@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # 1. Prepare file naming
    prefix = sanitize_filename(file.filename)
    download_name = f"{prefix}_hashed.csv"

    # 2. Create a temporary file
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    
    try:
        # Read the uploaded content
        content = await file.read()
        lines = content.decode("utf-8", errors="replace").splitlines()
        reader = csv.reader(lines)
        
        # 3. Process Headers
        headers = next(reader, None)
        if not headers:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        col_map = [] # To store (index, type)
        out_headers = []

        for i, h in enumerate(headers):
            h_lower = h.lower()
            if "phone" in h_lower or "mobile" in h_lower:
                col_map.append((i, "phone"))
                out_headers.append(f"hashed_{h}")
            elif "email" in h_lower:
                col_map.append((i, "email"))
                out_headers.append(f"hashed_{h}")

        if not col_map:
            raise HTTPException(status_code=400, detail="No phone or email columns detected")

        # 4. Process Rows
        writer = csv.writer(temp_out)
        writer.writerow(out_headers)

        for row in reader:
            if not row: continue
            
            hashed_row = []
            for index, data_type in col_map:
                # Ensure index exists in the row to avoid IndexError
                val = row[index] if index < len(row) else ""
                
                if data_type == "phone":
                    hashed_row.append(sha256_hash(normalize_phone(val)))
                elif data_type == "email":
                    hashed_row.append(sha256_hash(normalize_email(val)))
            
            writer.writerow(hashed_row)

        temp_out.close()

        # 5. Return File and Cleanup
        # We use BackgroundTasks to delete the file AFTER it has been downloaded
        background_tasks.add_task(remove_file, temp_out.name)

        return FileResponse(
            path=temp_out.name,
            media_type="text/csv",
            filename=download_name
        )

    except Exception as e:
        if os.path.exists(temp_out.name):
            os.unlink(temp_out.name)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")