from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import hashlib, csv, re, os, tempfile, sqlite3

app = FastAPI(title="Meta Hash & Upload API")

# CORS (allow frontend dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- API Key ---
API_KEY = os.getenv("API_KEY", "TEST_KEY")  # replace with your key

def verify_api_key(api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# --- Phone normalization (Sri Lanka example) ---
def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "94" + phone
    return phone

# --- Email normalization ---
def normalize_email(email: str) -> str:
    return email.strip().lower()

# --- SHA256 hashing ---
def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# --- Simple SQLite logging ---
DB_FILE = "meta_upload_logs.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            rows_processed INTEGER,
            rows_hashed INTEGER,
            client TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def log_upload(filename, rows_processed, rows_hashed, client="default"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO logs (filename, rows_processed, rows_hashed, client) VALUES (?,?,?,?)",
              (filename, rows_processed, rows_hashed, client))
    conn.commit()
    conn.close()

# --- Hash CSV endpoint ---
@app.post("/hash_csv")
async def hash_csv(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV only")

    # Prepare output CSV
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)

    # Read input CSV
    reader = csv.reader((line.decode("utf-8", errors="ignore") for line in file.file))
    headers = next(reader, None)

    # Detect columns
    col_type = []
    for h in headers:
        h_lower = h.lower()
        if "phone" in h_lower or "mobile" in h_lower:
            col_type.append("phone")
        elif "email" in h_lower:
            col_type.append("email")
        else:
            col_type.append(None)

    # Output header
    output_headers = [h if col_type[i] else "" for i, h in enumerate(headers)]
    writer.writerow([h for h in output_headers if h])

    rows_processed = 0
    rows_hashed = 0

    for row in reader:
        rows_processed += 1
        hashed_row = []
        for i, val in enumerate(row):
            if col_type[i] == "phone":
                norm = normalize_phone(val)
                hashed_row.append(sha256_hash(norm))
            elif col_type[i] == "email":
                norm = normalize_email(val)
                hashed_row.append(sha256_hash(norm))
        if hashed_row:
            writer.writerow(hashed_row)
            rows_hashed += 1

    temp_out.close()

    # Log to DB
    log_upload(file.filename, rows_processed, rows_hashed)

    # Return JSON (for beginner dashboard)
    return JSONResponse({
        "filename": file.filename,
        "rows_processed": rows_processed,
        "rows_hashed": rows_hashed,
        "match_rate_estimate": f"{(rows_hashed/rows_processed*100):.2f}%" if rows_processed else "0%"
    })
