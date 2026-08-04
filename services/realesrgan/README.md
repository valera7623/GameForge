# Real-ESRGAN (CPU)

HTTP upscaler for GameForge Texture Upscaler. Uses `realesrgan-ncnn-vulkan` with **Mesa llvmpipe** (no GPU).

## API

- `GET /health`
- `POST /upscale` — multipart `image` + `scale` (`2`|`4`), optional `model`

## Models

| Name | Use |
|------|-----|
| `realesrgan-x4plus` (default) | General game textures, sharper, slower on CPU |
| `realesrgan-x4plus-anime` | Anime / stylized art |
| `realesr-animevideov3` | Faster CPU fallback (native ×2/×4) |

Env: `REALESRGAN_MODEL`, `REALESRGAN_TILE` (RAM; default `128`), `REALESRGAN_THREADS`, `REALESRGAN_TIMEOUT`.

## Compose

```bash
# .env
REALESRGAN_URL=http://realesrgan:8080

docker compose --profile ai up -d --build realesrgan
# recreate api/worker if they already run so they pick up REALESRGAN_URL
```

Expect tens of seconds per texture on a small CPU VPS; large inputs may take minutes.
