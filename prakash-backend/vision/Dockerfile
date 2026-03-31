FROM python:3.12-slim

WORKDIR /app

# System dependencies for opencv and ultralytics
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
RUN pip install --no-cache-dir \
    fastapi>=0.115 \
    uvicorn[standard]>=0.30 \
    ultralytics>=8.2 \
    opencv-python-headless>=4.10 \
    numpy>=1.26 \
    python-multipart>=0.0.9

# Copy inference server
COPY serve.py .

# Weights are mounted at runtime via docker-compose volume
# docker-compose maps ./vision/weights -> /app/weights
ENV YOLO_WEIGHTS=/app/weights/best.pt
ENV YOLO_CONF=0.25
ENV YOLO_IOU=0.45

EXPOSE 8001

CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8001"]
