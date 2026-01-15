# 1. Use the same slim base as the worker for consistency
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. Set the working directory
WORKDIR /app

# 3. Install dependencies 
# (FastAPI needs python-multipart for file uploads)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the code
COPY . .

# 5. Create the local uploads folder (used for temporary storage)
RUN mkdir -p uploads

# 6. Expose the port FastAPI runs on
EXPOSE 8000

# 7. Start Uvicorn
# 'main:app' assumes your file is main.py and your FastAPI instance is named 'app'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]