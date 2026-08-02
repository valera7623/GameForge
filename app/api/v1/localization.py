"""AI Localization endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, LocalizationRequest
from app.services import ai_localization

router = APIRouter(prefix="/localization", tags=["localization"])


@router.post("", response_model=GenerationResponse)
async def localize(
    body: LocalizationRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.LOCALIZATION,
        input_data=body.model_dump(mode="json"),
        title=f"Localize {len(body.texts)} keys → {', '.join(body.target_langs[:5])}",
        project_id=body.project_id,
        run=lambda: ai_localization.localize(
            body.texts, body.source_lang, body.target_langs, body.export_format
        ),
    )


@router.get("/languages")
async def list_languages():
    return {"languages": ai_localization.SUPPORTED_LANGS}
