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

# --- STAGE 1: THE WATERMARKER (CPU Intensive) ---
async def watermark_image_task(ctx, file_path: str, logo_url: str = GOOGLE_LOGO):
    worker_id = os.getenv("HOSTNAME", "local-worker")
    job_id = ctx.get('job_id', 'manual')
    
    # Simulate Latency
    wait_time = random.randint(3, 8)
    print(f"⏳ [STAGE 1] Job {job_id}: Processing image {Path(file_path).name} ({wait_time}s)...")
    await asyncio.sleep(wait_time)
    
    # Download Logo
    async with httpx.AsyncClient() as client:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = await client.get(logo_url, headers=headers, timeout=10.0)
            response.raise_for_status()
            logo_data = BytesIO(response.content)
        except Exception as e:
            print(f"❌ [STAGE 1] Logo Download Failed: {e}")
            return {"status": "error", "reason": "logo_download_failed"}

    # Process Image
    abs_path = Path(file_path).resolve()
    try:
        with Image.open(abs_path) as base_image, Image.open(logo_data) as logo:
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            base_w, base_h = base_image.size
            logo.thumbnail((base_w // 5, base_h // 5))
            
            position = (base_w - logo.size[0] - 10, 10)
            base_image = base_image.convert('RGBA')
            base_image.paste(logo, position, mask=logo)
            
            # Save final product
            output_filename = f"watermarked_{abs_path.name}"
            output_path = abs_path.parent / output_filename
            base_image.convert('RGB').save(str(output_path), "JPEG")
            
            print(f"✅ [STAGE 1] Success! Enqueueing Stage 2 for {output_filename}")
            
            # --- TRIGGER STAGE 2 ---
            # We pass the path of the NEW watermarked image to the next function
            await ctx['redis'].enqueue_job('upload_to_central_task', file_path=str(output_path))
            
            return {"status": "watermarked", "output": str(output_path)}

    except UnidentifiedImageError:
        print(f"❌ [STAGE 1] Invalid Image Data")
        return {"status": "error", "reason": "invalid_image"}
    except Exception as e:
        print(f"❌ [STAGE 1] Unexpected Error: {e}")
        return {"status": "error", "reason": str(e)}


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