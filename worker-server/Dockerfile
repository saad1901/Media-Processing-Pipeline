# 1. Use a slim Python image to keep the size small
FROM python:3.12-slim

# 2. Set environment variables
# Prevents Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Install system dependencies for Pillow (images) and Networking
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Set the working directory inside the container
WORKDIR /app

# 5. Copy and install requirements
# Copying requirements first leverages Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy your project code
COPY . .

# 7. Start the ARQ worker
# 'worker.WorkerSettings' assumes your file is named worker.py 
# and contains the WorkerSettings class
CMD ["arq", "worker.WorkerSettings"]