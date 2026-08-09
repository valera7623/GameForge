"""AI Localization endpoint."""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, LocalizationCsvParseResponse, LocalizationRequest
from app.services import ai_localization
from app.services.ai_localization import LocalizationCsvError

router = APIRouter(prefix="/localization", tags=["localization"])

_CSV_ERROR_DETAIL = {
    "empty_csv": "CSV file is empty",
    "csv_need_header_and_row": "CSV needs a header row and at least one data row",
    "csv_no_key_column": "CSV must have a key column (key / id / name)",
    "csv_no_source_column": "CSV must have a source column (source / en / text / value)",
    "csv_no_rows": "CSV has no usable rows",
}


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
        localization_word_count=ai_localization.count_source_words(body.texts),
        run=lambda: ai_localization.localize(
            body.texts,
            body.source_lang,
            body.target_langs,
            body.export_format,
            body.glossary,
            body.include_qa,
            body.include_pseudo,
        ),
    )


@router.post("/pseudo")
async def pseudo_only(
    body: LocalizationRequest,
    user: User = Depends(get_current_user),
):
    """Pseudo-localize source strings without burning generation quota."""
    _ = user
    return {
        "source_lang": body.source_lang,
        "pseudo": ai_localization.build_pseudo(body.texts),
        "key_count": len(body.texts),
    }


@router.post("/parse-csv", response_model=LocalizationCsvParseResponse)
async def parse_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Parse uploaded CSV into localization texts (no quota / generation)."""
    _ = user
    if file.size is not None and file.size > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CSV too large (max 2MB)")
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CSV too large (max 2MB)")
    try:
        parsed = ai_localization.parse_source_csv(raw)
    except LocalizationCsvError as exc:
        code = str(exc)
        if code.startswith("csv_duplicate_key:"):
            key = code.split(":", 1)[1]
            raise HTTPException(status_code=400, detail=f"Duplicate key in CSV: {key}") from exc
        raise HTTPException(
            status_code=400,
            detail=_CSV_ERROR_DETAIL.get(code, "Could not parse CSV"),
        ) from exc
    return LocalizationCsvParseResponse(**parsed)


@router.get("/languages")
async def list_languages():
    return {"languages": ai_localization.SUPPORTED_LANGS}
