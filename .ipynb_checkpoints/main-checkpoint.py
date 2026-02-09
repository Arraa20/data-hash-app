from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib, csv, os, tempfile, re

app = FastAPI(title="Universal Data Anonymization API")

# ------------------- API Key -------------------
API_KEY = os.getenv("API_KEY", "testkey")  # fallback key for testing
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ------------------- CORS -------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- Helpers -------------------
def normalize_phone(p: str) -> str:
    if not p:
        return ""
    p = re.sub(r"\D", "", p)
    if p.startswith("0"):
        return "94" + p[1:]
    if p.startswith("7") and len(p) == 9:
        return "94" + p
    return p

def normalize_email(e: str) -> str:
    if not e:
        return ""
    return e.strip().lower()

def sha256(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()

# ------------------- Endpoint -------------------
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV only")

    # Create temporary output file
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)

    # Decode lines safely
    try:
        reader = csv.reader((line.decode("utf-8", errors="ignore") for line in file.file))
        headers = next(reader)
    except Exception as e:
        temp_out.close()
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")

    # Detect columns
    schema = []
    col_type = []
    for h in headers:
        h_lower = h.lower()
        if "phone" in h_lower or "mobile" in h_lower:
            schema.append("PHONE")
            col_type.append("phone")
        elif "email" in h_lower:
            schema.append("EMAIL")
            col_type.append("email")
        else:
            schema.append(None)
            col_type.append(None)

    # Write header
    writer.writerow([s for s in schema if s])

    # Process rows
    for row in reader:
        if not any(row):
            continue  # skip empty rows
        hashed_row = []
        for i, val in enumerate(row):
            if col_type[i] == "phone":
                hashed_row.append(sha256(normalize_phone(val)))
            elif col_type[i] == "email":
                hashed_row.append(sha256(normalize_email(val)))
        if hashed_row:
            writer.writerow(hashed_row)

    temp_out.close()
    return FileResponse(temp_out.name, filename="meta_hashed.csv", media_type="text/csv")
