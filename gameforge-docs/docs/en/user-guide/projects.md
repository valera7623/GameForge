# Projects

Projects group assets for a game title and engine.

## Create a project

1. Open **Projects** (or create from a tool form).
2. Set **name**, optional **description**, and **engine** (`unreal`, `unity`, `godot`, or `other`).
3. Save — you receive a project id used by tool APIs.

## Attach generations

Most tools accept an optional `project_id`. When set, results are linked to that project for history and export.

## Export

Download a ZIP of project assets:

```bash
curl -s -X GET "http://localhost:8000/api/v1/projects/$PID/export" \
  -H "Authorization: Bearer $TOKEN" -o game-assets.zip
```

In the UI, use the project export action when available.

## Ownership

You own projects you create. Studio org features (shared seats) are covered in [Team](team.md).
