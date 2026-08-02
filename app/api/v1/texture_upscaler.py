"""AI Texture Upscaler endpoint."""

import base64
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import enqueue_tool, run_tool
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse
from app.services import ai_texture_upscaler

router = APIRouter(prefix="/texture-upscaler", tags=["texture-upscaler"])
settings = get_settings()


@router.post("", response_model=GenerationResponse)
async def upscale(
    request: Request,
    file: UploadFile = File(...),
    scale: int = Form(2),
    enhance: bool = Form(True),
    project_id: str | None = Form(None),
    async_mode: bool | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if async_mode is None:
        async_mode = bool(settings.REALESRGAN_URL)

    if file.content_type not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        raise HTTPException(status_code=400, detail="Only PNG/JPG/WEBP supported")

    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    pid = UUID(project_id) if project_id else None
    input_data = {"filename": file.filename, "scale": scale, "enhance": enhance}
    title = f"Upscale {scale}x: {file.filename}"

    if async_mode:
        def enqueue(gen):
            from app.tasks.upscale_task import upscale_texture_task

            task = upscale_texture_task.delay(
                str(gen.id),
                base64.b64encode(data).decode(),
                file.filename or "texture.png",
                scale,
                enhance,
            )
            gen.celery_task_id = task.id

        return await enqueue_tool(
            request=request,
            db=db,
            user=user,
            tool=ToolType.TEXTURE_UPSCALER,
            input_data=input_data,
            title=title,
            project_id=pid,
            enqueue=enqueue,
        )

    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.TEXTURE_UPSCALER,
        input_data=input_data,
        title=title,
        project_id=pid,
        run=lambda: ai_texture_upscaler.upscale_texture(
            data, file.filename or "texture.png", scale, enhance
        ),
        asset_urls_from=lambda o: [o.get("url")],
    )
