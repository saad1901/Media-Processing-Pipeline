import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File
from arq import create_pool
from arq.connections import RedisSettings

UPLOAD_DIR = Path("uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Connecting to Redis at {REDIS_HOST}...")
    try:
        app.state.arq_pool = await create_pool(RedisSettings(host=REDIS_HOST))
        print("✅ Redis Connection Pool Created.")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        raise e
    
    yield
    print("🛑 Closing Redis connection...")
    await app.state.arq_pool.close()

app = FastAPI(
    title="Media Processor API",
    lifespan=lifespan
)

@app.post("/media")
async def upload_media(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"📂 File saved to shared volume: {file_path}")
    except Exception as e:
        return {"status": "error", "message": f"Could not save file: {str(e)}"}

    await app.state.arq_pool.enqueue_job(
        'watermark_image_task', 
        file_path=str(file_path)
    )
    
    print(f"📨 Job enqueued for {file.filename}")

    return {
        "message": "Task Enqueued", 
        "filename": file.filename,
        "storage_path": str(file_path)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)