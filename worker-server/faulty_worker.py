import os
import random
import asyncio
import httpx
from io import BytesIO
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from arq import Retry
from arq.connections import RedisSettings

# 1. Configuration
GOOGLE_LOGO = 'https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png'
CENTRAL_SERVER_URL = "http://host.docker.internal:8003/upload-final"

# --- THE "SUDDEN DEATH" WORKER ---
async def watermark_image_task(ctx, file_path: str, logo_url: str = GOOGLE_LOGO):
    job_id = ctx.get('job_id', 'manual')
    
    print(f"⏳ [STAGE 1] Job {job_id}: Processing image {Path(file_path).name}...")
    
    # Simulate some work
    await asyncio.sleep(2)
    
    # CRITICAL FAILURE: No signals, no cleanup, no notifications.
    # The process simply ceases to exist.
    print(f"💀 [CRASH] System failure in Job {job_id}! Exiting process now...")
    
    import os
    os._exit(1)  # This kills the worker instantly.

# --- STAGE 2: THE SHIPPER (Network Intensive + Retries) ---
async def upload_to_central_task(ctx, file_path: str):
    worker_id = os.getenv("HOSTNAME", "local-worker")
    job_id = ctx.get('job_id', 'manual')
    file_name = Path(file_path).name

    print(f"🚀 [STAGE 2] Shipping {file_name} to Central Server...")

    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "image/jpeg")}
                data = {"worker_name": worker_id}
                res = await client.post(CENTRAL_SERVER_URL, files=files, data=data, timeout=15.0)
                res.raise_for_status()
            
            print(f"✨ [STAGE 2] JOB COMPLETE: {file_name} successfully stored.")
            # Optional: Clean up processed file after upload
            # os.remove(file_path)
            return {"status": "shipped", "worker": worker_id}

        except Exception as e:
            # If Central Server is down, we retry ONLY this stage
            # Backoff: 10s, 20s, 30s... up to 5 times
            if ctx['job_try'] <= 5:
                wait_time = ctx['job_try'] * 10
                print(f"⚠️ [STAGE 2] Server 8003 unreachable. Retry {ctx['job_try']}/5 in {wait_time}s...")
                raise Retry(defer=wait_time)
            else:
                print(f"🔥 [STAGE 2] FATAL: Could not reach Central Server after 5 tries.")
                return {"status": "failed", "reason": "server_unreachable"}


class WorkerSettings:
    # IMPORTANT: Register both functions here
    functions = [watermark_image_task, upload_to_central_task]
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=6379
    )
