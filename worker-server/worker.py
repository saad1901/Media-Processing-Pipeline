from arq.connections import RedisSettings
import httpx
import asyncio
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from pathlib import Path
import os
import random

# Using a very stable Google PNG logo
GOOGLE_LOGO = 'https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png'
async def watermark_image_task(ctx, file_path: str, logo_url: str = GOOGLE_LOGO):
    worker_id = os.getenv("HOSTNAME", "local-worker")
    job_id = ctx.get('job_id') if isinstance(ctx, dict) else "manual"
    
    # 1. Simulate Latency
    wait_time = random.randint(3, 8)
    print(f"⏳ [JOB {job_id}] Worker {worker_id}: Sleeping for {wait_time}s...")
    await asyncio.sleep(wait_time)
    
    # 2. Download Logo with Headers
    print(f"📡 [JOB {job_id}] Downloading logo from {logo_url}...")
    async with httpx.AsyncClient() as client:
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = await client.get(logo_url, headers=headers, timeout=10.0)
            response.raise_for_status()
            logo_data = BytesIO(response.content)
            print(f"✅ [JOB {job_id}] Logo download successful.")
        except Exception as e:
            print(f"❌ [JOB {job_id}] DOWNLOAD FAILED: {str(e)}")
            return {"status": "error", "reason": "download_failed"}

    # 3. Process Image
    abs_path = Path(file_path).resolve()
    print(f"🎨 [JOB {job_id}] Processing image: {abs_path.name}")
    
    try:
        with Image.open(abs_path) as base_image, Image.open(logo_data) as logo:
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            # Scale logo to 20% of base image width
            base_w, base_h = base_image.size
            logo.thumbnail((base_w // 5, base_h // 5))
            lw, lh = logo.size
            
            # Top-right position with padding
            position = (base_w - lw - 10, 10)
            
            base_image = base_image.convert('RGBA')
            base_image.paste(logo, position, mask=logo)
            
            output_filename = f"watermarked_{abs_path.name}"
            output_path = abs_path.parent / output_filename
            base_image.convert('RGB').save(str(output_path), "JPEG")
            print(f"💾 [JOB {job_id}] Image saved locally: {output_filename}")

    except UnidentifiedImageError:
        print(f"❌ [JOB {job_id}] ERROR: Logo URL returned data that isn't a valid image.")
        return {"status": "error", "reason": "invalid_image_data"}
    except FileNotFoundError:
        print(f"❌ [JOB {job_id}] ERROR: Base image not found at {abs_path}")
        return {"status": "error", "reason": "file_not_found"}
    except Exception as e:
        print(f"❌ [JOB {job_id}] UNEXPECTED ERROR: {str(e)}")
        return {"status": "error", "reason": str(e)}

    # 4. Ship to Central Server (8003)
    # Using host.docker.internal to reach your local server from the container
    CENTRAL_SERVER_URL = "http://host.docker.internal:8003/upload-final"
    
    print(f"🚀 [JOB {job_id}] Shipping to Central Server...")
    async with httpx.AsyncClient() as client:
        try:
            with open(output_path, "rb") as f:
                files = {"file": (output_filename, f, "image/jpeg")}
                data = {"worker_name": worker_id}
                res = await client.post(CENTRAL_SERVER_URL, files=files, data=data, timeout=15.0)
                
            if res.status_code == 200:
                print(f"✨ [JOB {job_id}] SUCCESSFULLY STORED ON CENTRAL SERVER")
                return {"status": "success", "worker": worker_id}
            else:
                print(f"⚠️ [JOB {job_id}] Central Server returned status: {res.status_code}")
                return {"status": "server_error", "code": res.status_code}
        except Exception as e:
            print(f"❌ [JOB {job_id}] FAILED TO REACH CENTRAL SERVER: {str(e)}")
            return {"status": "upload_failed", "reason": str(e)}

class WorkerSettings:
    functions = [watermark_image_task]
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"), 
        port=6379
    )