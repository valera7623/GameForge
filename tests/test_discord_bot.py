"""Tests for AI Discord Bot helpers."""

from __future__ import annotations

import re

from app.services.ai_discord_bot import (
    analyze_community,
    decrypt_bot_token,
    encrypt_bot_token,
    moderate_message,
    run_builtin_command,
)


def test_token_roundtrip():
    enc = encrypt_bot_token("discord-bot-token-abcdef")
    assert enc != "discord-bot-token-abcdef"
    assert decrypt_bot_token(enc) == "discord-bot-token-abcdef"


def test_moderate_spam_and_clean():
    bad = moderate_message("FREE NITRO http://evil.test discord.gg/spam", lang="en")
    assert bad["flagged"] is True
    assert bad["action"] in ("delete", "warn", "timeout")
    good = moderate_message("Looking for dungeon co-op tonight!", lang="en")
    assert good["flagged"] is False


def test_commands_roll_help():
    roll = run_builtin_command("roll", "d20", lang="en")
    assert roll["ok"] and "d20" in roll["response"]
    help_out = run_builtin_command("help", lang="en")
    assert help_out["ok"] and "game" in help_out["response"]


def test_analyze_community_ru():
    result = analyze_community(
        {
            "bot_name": "Dungeon Bot",
            "messages": [
                "Great update, love the combat!",
                "FREE NITRO http://scam.test",
                "Идиот, игра мусор",
            ],
        },
        lang="ru",
    )
    assert result["summary"]["total_messages"] == 3
    assert result["summary"]["moderated"] >= 1
    assert re.search(r"[А-Яа-яЁё]", result["summary_text"])
