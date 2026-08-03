# Deployment

How to run GameForge in local Docker and on a production VPS.

## Contents

| Page | Topics |
|------|--------|
| [Docker](docker.md) | Compose profiles, local stack |
| [VPS](vps.md) | Caddy, DNS, public S3, CI deploy |
| [Troubleshooting](troubleshooting.md) | Common failures |

## Environments

| Mode | Compose files | Notes |
|------|---------------|-------|
| Local | `docker-compose.yml` | Ports published; mock AI OK |
| Production | `+ docker-compose.prod.yml` | Caddy, no host ports on API, migrate job |
| On-prem | `+ docker-compose.onprem.yml` | Forces enterprise plan, billing off |
