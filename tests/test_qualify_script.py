"""The live qualification driver, checked where it decides not to spend.

The run this drives costs real money and is authorized one at a time, so what
is worth testing offline is the refusal before the spend: a profile the caller
did not expect must stop the driver before it creates a database, let alone
calls a provider. Everything after that point is the harness's own, and has its
own suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import qualify


def test_main_refuses_a_profile_the_caller_did_not_expect(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A verdict binds its execution profile, so a surprise one spends nothing."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-not-a-real-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-5.6-terra")
    monkeypatch.setenv("OPENROUTER_PROVIDER", "openai/flex")
    monkeypatch.setenv("OPENROUTER_REASONING_EFFORT", "high")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    # No database is reachable under this name: reaching one would be the bug.
    monkeypatch.setenv("CAOS_TEST_POSTGRES_URL", "postgresql://nobody@127.0.0.1:1/none")
    monkeypatch.setenv(
        "CAOS_MODEL_PRICE", "openai/gpt-5.6-terra,0.000002,0.000012,2026-09-16"
    )

    code = qualify.main(
        [
            str(Path(__file__).resolve().parents[1] / "qualification/vmo2-fy2025"),
            "--expect-identity",
            "openrouter/google-ai-studio/high/65536",
            "--ceiling",
            "22.00",
        ]
    )

    assert code == 2
    assert "nothing was spent" in capsys.readouterr().err


def test_main_is_the_driver_the_record_names() -> None:
    """The driver is in the tree, not in a temporary directory that can vanish."""
    assert (Path(__file__).resolve().parents[1] / "scripts/qualify.py").is_file()
    assert qualify.main.__module__ == "qualify"
