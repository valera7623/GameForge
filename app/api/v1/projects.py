"""Projects CRUD + ZIP export."""

import io
import json
import zipfile
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.generation import Generation, GenerationStatus
from app.models.project import GameEngine, Project
from app.models.user import User
from app.schemas import (
    ProjectCreate,
    ProjectGlossaryResponse,
    ProjectGlossaryUpdate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.ai_localization import normalize_glossary
from app.services.storage import download_bytes

router = APIRouter(prefix="/projects", tags=["projects"])


def _engine(value: str) -> GameEngine:
    try:
        return GameEngine(value.lower())
    except ValueError:
        return GameEngine.OTHER


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        owner_id=user.id,
        name=body.name,
        description=body.description,
        engine=_engine(body.engine),
    )
    db.add(project)
    await db.flush()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        engine=project.engine.value,
        cover_url=project.cover_url,
        created_at=project.created_at,
        updated_at=project.updated_at,
        generations_count=0,
    )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project, func.count(Generation.id))
        .outerjoin(Generation, Generation.project_id == Project.id)
        .where(Project.owner_id == user.id)
        .group_by(Project.id)
        .order_by(Project.updated_at.desc())
    )
    rows = result.all()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            engine=p.engine.value,
            cover_url=p.cover_url,
            created_at=p.created_at,
            updated_at=p.updated_at,
            generations_count=count or 0,
        )
        for p, count in rows
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, user, project_id)
    count = await db.scalar(select(func.count(Generation.id)).where(Generation.project_id == project.id))
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        engine=project.engine.value,
        cover_url=project.cover_url,
        created_at=project.created_at,
        updated_at=project.updated_at,
        generations_count=count or 0,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, user, project_id)
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.engine is not None:
        project.engine = _engine(body.engine)
    await db.flush()
    return await get_project(project_id, user, db)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, user, project_id)
    await db.delete(project)


@router.get("/{project_id}/glossary", response_model=ProjectGlossaryResponse)
async def get_project_glossary(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, user, project_id)
    glossary = normalize_glossary(project.localization_glossary) or {}
    return ProjectGlossaryResponse(project_id=project.id, glossary=glossary)


@router.put("/{project_id}/glossary", response_model=ProjectGlossaryResponse)
async def put_project_glossary(
    project_id: UUID,
    body: ProjectGlossaryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, user, project_id)
    project.localization_glossary = body.glossary or {}
    await db.flush()
    return ProjectGlossaryResponse(project_id=project.id, glossary=project.localization_glossary)


@router.get("/{project_id}/export")
async def export_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, user, project_id)
    result = await db.execute(
        select(Generation).where(
            Generation.project_id == project.id,
            Generation.status == GenerationStatus.COMPLETED,
        )
    )
    gens = result.scalars().all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "engine": project.engine.value,
                "description": project.description,
            },
            "assets": [],
        }
        for gen in gens:
            folder = f"{gen.tool.value}/{gen.id}"
            meta = {
                "id": str(gen.id),
                "tool": gen.tool.value,
                "title": gen.title,
                "input": gen.input_data,
                "output": gen.output_data,
                "created_at": gen.created_at.isoformat() if gen.created_at else None,
            }
            zf.writestr(f"{folder}/meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
            if gen.output_data:
                zf.writestr(
                    f"{folder}/output.json",
                    json.dumps(gen.output_data, ensure_ascii=False, indent=2, default=str),
                )
            for j, url in enumerate(gen.asset_urls or []):
                data = download_bytes(url) if isinstance(url, str) else None
                if data:
                    ext = "bin"
                    if ".png" in str(url):
                        ext = "png"
                    elif ".wav" in str(url):
                        ext = "wav"
                    elif ".mp3" in str(url):
                        ext = "mp3"
                    zf.writestr(f"{folder}/asset_{j}.{ext}", data)
            manifest["assets"].append({"id": str(gen.id), "tool": gen.tool.value, "title": gen.title})
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    buf.seek(0)
    filename = f"{project.name.replace(' ', '_').lower()}_assets.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _owned_project(db: AsyncSession, user: User, project_id: UUID) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
