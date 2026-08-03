# Tools

GameForge ships **seven** AI tools. With `USE_MOCK_AI=true` they run without paid keys; with `USE_MOCK_AI=false` they call external providers (OpenAI / ProxyAPI and optional services).

## Level Designer

- **Input:** natural-language level brief (optional project)
- **Output:** tilemap JSON + canvas preview
- **API:** `POST /api/v1/level-designer`

## Quest Generator

- **Input:** quest / story prompt
- **Output:** quest structure, dialogues, branches as JSON
- **API:** `POST /api/v1/quest-generator`

## Texture Upscaler

- **Input:** uploaded image + scale (2× / 4×)
- **Output:** upscaled PNG URL (Real-ESRGAN service or PIL mock)
- **API:** `POST /api/v1/texture-upscaler`
- Heavy work may run on the **Celery worker**

## Character Creator

- **Input:** character description (required; regenerate keeps last body)
- **Output:** image URL in object storage
- **API:** `POST /api/v1/character-creator`

## Sound Designer

- **Input:** prompt + kind (sfx / music / voice)
- **Output:** audio file URL (mock waveform or provider)
- **API:** `POST /api/v1/sound-designer`

## Playtester

- **Input:** design doc / feature description
- **Output:** QA-style report JSON (issues, severity, suggestions)
- **API:** `POST /api/v1/playtester`

## Localization

- **Input:** source strings / JSON + target languages
- **Output:** translated JSON or CSV
- **API:** `POST /api/v1/localization`

## Asset URLs

Generated files are stored in MinIO. In production, browsers open **signed** URLs under `https://<domain>/s3/...`. If a link fails, check [Deployment → VPS](../deployment/vps.md) (`S3_PUBLIC_ENDPOINT`).
