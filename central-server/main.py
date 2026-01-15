import os
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form

app = FastAPI()

# Configuration
STORAGE_DIR = Path("./central_storage")
LOG_FILE = Path("worker_activity.log")

# Ensure the storage directory exists
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/upload-final")
async def receive_from_worker(
    file: UploadFile = File(...), 
    worker_name: str = Form(...)
):
    # 1. Save the Image
    save_path = STORAGE_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. Generate Log Entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] WORKER: {worker_name} | IMAGE: {file.filename}\n"
    
    # 3. Write to Text File (Mode 'a' means Append)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    
    print(f"Log updated: {log_entry.strip()}")
    
    return {
        "status": "stored_and_logged",
        "worker": worker_name,
        "timestamp": timestamp
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)