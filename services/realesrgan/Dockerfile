# Real-ESRGAN on CPU: ncnn binary + Mesa llvmpipe (Vulkan software rasterizer).
# No NVIDIA GPU required. Expect slower upscales than GPU — fine for texture demos.
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl unzip ca-certificates \
        libvulkan1 libgomp1 mesa-vulkan-drivers \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/realesrgan

# Official Ubuntu ncnn build (includes models/)
ARG REALESRGAN_URL=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip
ARG REALESRGAN_SHA256=e5aa6eb131234b87c0c51f82b89390f5e3e642b7b70f2b9bbe95b6a285a40c96

RUN curl -fsSL -o /tmp/realesrgan.zip "$REALESRGAN_URL" \
    && echo "${REALESRGAN_SHA256}  /tmp/realesrgan.zip" | sha256sum -c - \
    && unzip -q /tmp/realesrgan.zip -d /opt/realesrgan \
    && chmod +x /opt/realesrgan/realesrgan-ncnn-vulkan \
    && rm -f /tmp/realesrgan.zip /opt/realesrgan/input.jpg /opt/realesrgan/input2.jpg /opt/realesrgan/onepiece_demo.mp4 \
    && test -x /opt/realesrgan/realesrgan-ncnn-vulkan \
    && test -d /opt/realesrgan/models

WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn python-multipart
COPY app.py .

ENV REALESRGAN_BIN=/opt/realesrgan/realesrgan-ncnn-vulkan \
    REALESRGAN_MODELS=/opt/realesrgan/models \
    REALESRGAN_MODEL=realesrgan-x4plus \
    REALESRGAN_TILE=128 \
    REALESRGAN_THREADS=1:2:2 \
    REALESRGAN_TIMEOUT=600

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
