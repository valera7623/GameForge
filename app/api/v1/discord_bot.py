"""AI Discord Bot API — configure, commands, moderation preview, community analytics."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.discord_bot import DiscordBotCommand, DiscordBotConfig, DiscordBotMessage
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import (
    DiscordAnalyzeRequest,
    DiscordCommandCreate,
    DiscordCommandOut,
    DiscordCommandUpdate,
    DiscordConfigureRequest,
    DiscordModerateRequest,
    DiscordSimulateCommandRequest,
    DiscordStatusOut,
    GenerationResponse,
)
from app.services import ai_discord_bot as bot_svc

router = APIRouter(prefix="/discord-bot", tags=["discord-bot"])


async def _get_config(db: AsyncSession, user_id: UUID) -> DiscordBotConfig | None:
    res = await db.execute(
        select(DiscordBotConfig).where(DiscordBotConfig.user_id == user_id).order_by(DiscordBotConfig.updated_at.desc())
    )
    return res.scalars().first()


async def _require_config(db: AsyncSession, user_id: UUID) -> DiscordBotConfig:
    cfg = await _get_config(db, user_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Discord bot not configured yet")
    return cfg


def _seed_default_commands(config_id: UUID) -> list[DiscordBotCommand]:
    rows = []
    for c in bot_svc.DEFAULT_COMMANDS:
        rows.append(
            DiscordBotCommand(
                config_id=config_id,
                command=c["command"],
                description=c.get("description") or "",
                usage=c.get("usage") or f"!{c['command']}",
                response=c.get("response") or "",
                category=c.get("category") or "custom",
                is_active=True,
            )
        )
    return rows


@router.post("/configure", response_model=DiscordStatusOut)
async def configure_bot(
    body: DiscordConfigureRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _get_config(db, user.id)
    created = False
    if not cfg:
        cfg = DiscordBotConfig(user_id=user.id)
        db.add(cfg)
        created = True
        await db.flush()

    cfg.bot_name = body.bot_name.strip() or cfg.bot_name
    cfg.guild_id = body.guild_id.strip()
    cfg.channel_id = body.channel_id.strip()
    cfg.prefix = (body.prefix or "!").strip()[:8] or "!"
    cfg.moderation_enabled = body.moderation_enabled
    cfg.welcome_enabled = body.welcome_enabled
    cfg.analytics_enabled = body.analytics_enabled
    cfg.moderation = {**bot_svc.default_moderation(), **(body.moderation or {})}
    cfg.welcome = {**bot_svc.default_welcome(body.bot_name), **(body.welcome or {})}
    cfg.analytics = {**bot_svc.default_analytics(), **(body.analytics or {})}
    if body.game_info:
        cfg.game_info = body.game_info
    if body.bot_token and body.bot_token.strip() and not body.bot_token.strip().startswith("••"):
        raw = body.bot_token.strip()
        cfg.bot_token_enc = bot_svc.encrypt_bot_token(raw)
        cfg.token_last4 = raw[-4:]
    if body.mark_connected is not None:
        cfg.is_connected = bool(body.mark_connected) and bool(cfg.bot_token_enc) and bool(cfg.guild_id)
    if not cfg.stats:
        cfg.stats = bot_svc.default_stats()

    await db.flush()

    if created:
        for row in _seed_default_commands(cfg.id):
            db.add(row)
        await db.flush()

    cmds = await db.execute(
        select(DiscordBotCommand).where(DiscordBotCommand.config_id == cfg.id).order_by(DiscordBotCommand.command)
    )
    commands = [_cmd_out(c) for c in cmds.scalars().all()]
    public = bot_svc.config_public_dict(cfg, lang=body.lang)
    public["commands"] = commands
    return DiscordStatusOut(**public)


@router.get("/status", response_model=DiscordStatusOut)
async def bot_status(
    lang: str = "en",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _get_config(db, user.id)
    if not cfg:
        return DiscordStatusOut(
            id=None,
            bot_name="GameForge Bot",
            guild_id="",
            channel_id="",
            prefix="!",
            token_masked=None,
            has_token=False,
            moderation_enabled=True,
            welcome_enabled=True,
            analytics_enabled=True,
            moderation=bot_svc.default_moderation(),
            welcome=bot_svc.default_welcome(),
            analytics=bot_svc.default_analytics(),
            game_info={},
            is_connected=False,
            status="offline",
            status_label=bot_svc._t(lang, "status_missing"),
            stats=bot_svc.default_stats(),
            commands=[],
            updated_at=None,
        )
    cmds = await db.execute(
        select(DiscordBotCommand).where(DiscordBotCommand.config_id == cfg.id).order_by(DiscordBotCommand.command)
    )
    public = bot_svc.config_public_dict(cfg, lang=lang)
    public["commands"] = [_cmd_out(c) for c in cmds.scalars().all()]
    return DiscordStatusOut(**public)


def _cmd_out(c: DiscordBotCommand) -> DiscordCommandOut:
    return DiscordCommandOut(
        id=c.id,
        command=c.command,
        description=c.description,
        usage=c.usage,
        response=c.response,
        category=c.category,
        is_active=c.is_active,
    )


@router.get("/commands", response_model=list[DiscordCommandOut])
async def list_commands(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _require_config(db, user.id)
    res = await db.execute(
        select(DiscordBotCommand).where(DiscordBotCommand.config_id == cfg.id).order_by(DiscordBotCommand.command)
    )
    return [_cmd_out(c) for c in res.scalars().all()]


@router.post("/command", response_model=DiscordCommandOut, status_code=status.HTTP_201_CREATED)
async def create_command(
    body: DiscordCommandCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _require_config(db, user.id)
    name = body.command.strip().lstrip("/!").lower()
    if not name:
        raise HTTPException(status_code=400, detail="command required")
    existing = await db.execute(
        select(DiscordBotCommand).where(DiscordBotCommand.config_id == cfg.id, DiscordBotCommand.command == name)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Command already exists")
    row = DiscordBotCommand(
        config_id=cfg.id,
        command=name,
        description=body.description.strip(),
        usage=body.usage.strip() or f"{cfg.prefix}{name}",
        response=body.response,
        category=body.category or "custom",
        is_active=body.is_active,
    )
    db.add(row)
    await db.flush()
    return _cmd_out(row)


@router.patch("/command/{command_id}", response_model=DiscordCommandOut)
async def update_command(
    command_id: UUID,
    body: DiscordCommandUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _require_config(db, user.id)
    res = await db.execute(
        select(DiscordBotCommand).where(DiscordBotCommand.id == command_id, DiscordBotCommand.config_id == cfg.id)
    )
    row = res.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Command not found")
    if body.description is not None:
        row.description = body.description
    if body.usage is not None:
        row.usage = body.usage
    if body.response is not None:
        row.response = body.response
    if body.category is not None:
        row.category = body.category
    if body.is_active is not None:
        row.is_active = body.is_active
    await db.flush()
    return _cmd_out(row)


@router.delete("/command/{command_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_command(
    command_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _require_config(db, user.id)
    res = await db.execute(
        select(DiscordBotCommand).where(DiscordBotCommand.id == command_id, DiscordBotCommand.config_id == cfg.id)
    )
    row = res.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Command not found")
    await db.delete(row)
    await db.flush()


@router.post("/moderate")
async def moderate_preview(
    body: DiscordModerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _get_config(db, user.id)
    moderation = (cfg.moderation if cfg else None) or bot_svc.default_moderation()
    result = bot_svc.moderate_message(body.content, lang=body.lang, moderation=moderation)
    if cfg and result.get("flagged"):
        db.add(
            DiscordBotMessage(
                config_id=cfg.id,
                guild_id=cfg.guild_id,
                channel_id=cfg.channel_id,
                discord_user_id=body.user_id or "preview",
                content=body.content[:4000],
                is_moderated=True,
                moderated_by="auto",
                moderation_action=result.get("action"),
            )
        )
        stats = dict(cfg.stats or bot_svc.default_stats())
        stats["moderation_actions"] = int(stats.get("moderation_actions") or 0) + 1
        if result.get("action") == "warn":
            stats["warnings"] = int(stats.get("warnings") or 0) + 1
        cfg.stats = stats
        await db.flush()
    return result


@router.post("/simulate-command")
async def simulate_command(
    body: DiscordSimulateCommandRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _get_config(db, user.id)
    prefix = cfg.prefix if cfg else "!"
    game_info = (cfg.game_info if cfg else {}) or {}
    stats = (cfg.stats if cfg else None) or bot_svc.default_stats()
    custom = None
    catalog = []
    if cfg:
        res = await db.execute(select(DiscordBotCommand).where(DiscordBotCommand.config_id == cfg.id))
        rows = list(res.scalars().all())
        catalog = [
            {
                "command": r.command,
                "description": r.description,
                "usage": r.usage,
                "is_active": r.is_active,
            }
            for r in rows
        ]
        match = next((r for r in rows if r.command == body.command.strip().lstrip("/!").lower()), None)
        if match:
            custom = match.response
    out = bot_svc.run_builtin_command(
        body.command,
        body.args or "",
        lang=body.lang,
        game_info=game_info,
        custom_response=custom,
        prefix=prefix,
        commands_catalog=catalog or None,
        stats=stats,
    )
    if cfg and out.get("ok"):
        st = dict(cfg.stats or bot_svc.default_stats())
        st["commands_run"] = int(st.get("commands_run") or 0) + 1
        cfg.stats = st
        await db.flush()
    return out


@router.post("/analyze", response_model=GenerationResponse)
async def analyze_community(
    body: DiscordAnalyzeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _get_config(db, user.id)
    payload = body.to_payload()
    if cfg:
        payload.setdefault("bot_name", cfg.bot_name)
        payload.setdefault("moderation", cfg.moderation)
    title = f"Discord: {payload.get('bot_name') or 'Community'}"
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.DISCORD_BOT,
        input_data=payload,
        title=title[:200],
        project_id=body.project_id,
        run=lambda: _run_analyze(payload, body.lang),
    )


async def _run_analyze(payload: dict, lang: str):
    return bot_svc.analyze_community(payload, lang=lang)


@router.get("/analytics")
async def analytics_snapshot(
    lang: str = "en",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _get_config(db, user.id)
    if not cfg:
        return {"configured": False, "stats": bot_svc.default_stats()}
    res = await db.execute(
        select(DiscordBotMessage)
        .where(DiscordBotMessage.config_id == cfg.id)
        .order_by(DiscordBotMessage.created_at.desc())
        .limit(200)
    )
    msgs = [m.content for m in res.scalars().all()]
    report = bot_svc.analyze_community(
        {"bot_name": cfg.bot_name, "messages": msgs, "moderation": cfg.moderation},
        lang=lang,
    )
    report["configured"] = True
    report["stats"] = cfg.stats or bot_svc.default_stats()
    return report


@router.get("/users")
async def list_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # MVP: derived from message log identities
    cfg = await _require_config(db, user.id)
    res = await db.execute(
        select(DiscordBotMessage).where(DiscordBotMessage.config_id == cfg.id).order_by(DiscordBotMessage.created_at.desc()).limit(500)
    )
    counts: dict[str, int] = {}
    for m in res.scalars().all():
        uid = m.discord_user_id or "unknown"
        counts[uid] = counts.get(uid, 0) + 1
    return [{"user_id": k, "messages_count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
