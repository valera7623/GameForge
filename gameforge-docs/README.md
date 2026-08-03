# GameForge Documentation Site

Professional documentation for the GameForge AI Game Dev Toolkit, built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## Features

- **Material theme** with dark/light mode
- **Full-text search**
- **English** and **Russian** (`mkdocs-static-i18n`, folder locales)
- **Mermaid diagrams**
- CI build via GitHub Actions on changes under `gameforge-docs/`

## Local preview

```bash
cd gameforge-docs

# One-time setup
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start dev server
mkdocs serve
```

Or use the helper script (creates venv automatically, port **8001** — API uses 8000):

```bash
cd gameforge-docs
./mkdocs.sh serve
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001).

Custom port: `DOCS_PORT=9000 ./mkdocs.sh serve`

## Build

```bash
./mkdocs.sh build --strict
```

Output: `site/`

## Docker image (optional)

From the repository root:

```bash
docker build -f gameforge-docs/Dockerfile --build-arg SITE_URL=https://docs.gameforge.website -t gameforge-docs .
```

## Structure

```
gameforge-docs/
├── mkdocs.yml
├── requirements.txt
├── mkdocs.sh
└── docs/
    ├── assets/          # Logo, favicon
    ├── en/              # English content
    └── ru/              # Russian content
```

## Customize

- Update `site_url` and `repo_url` in `mkdocs.yml` for your domain and repository.
- Replace assets under `docs/assets/` as needed.
