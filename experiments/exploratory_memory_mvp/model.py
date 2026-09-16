"""Minimal DashScope chat client for the exploratory-memory MVP.

The repository's shared provider intentionally enforces the historical
DeepSeek backbone.  This experiment has an explicit user-selected model
override, so it keeps the transport local rather than changing that shared
policy.  Only visible assistant content is returned or persisted.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from memory_validation.network import disable_proxy_environment  # noqa: E402
from memory_validation.provider import (  # noqa: E402
    ProviderError,
    _NoRedirect,
    parse_usage,
    visible_message,
)
from memory_validation.schemas import canonical  # noqa: E402
from memory_validation.telemetry import CallUsage, UsageTracker  # noqa: E402

MODEL = "qwen3.8-flash"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CHAT_URL = BASE_URL + "/chat/completions"
API_KEY_ENV = "DASHSCOPE_API_KEY"
PRICING_SOURCE = "https://help.aliyun.com/en/model-studio/qwen3-8-flash"
PRICING_TABLE_SOURCE = "https://help.aliyun.com/en/model-studio/model-pricing"


class DashScopeError(ProviderError):
    """Safe, detail-free model transport or response error."""


def load_dashscope_key(env_file: Path | None = None) -> str:
    """Read only ``DASHSCOPE_API_KEY`` without mutating the process environment."""

    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key and env_file is not None:
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                name, separator, value = line.strip().removeprefix("export ").partition("=")
                if separator and name.strip() == API_KEY_ENV:
                    key = value.strip().strip("\"'")
        except OSError:
            raise DashScopeError("Cannot read credential file") from None
    if not key:
        raise DashScopeError(f"{API_KEY_ENV} is not configured")
    return key


class DashScopeChatTransport:
    """Direct, no-redirect, no-retry transport for DashScope chat completion."""

    def __init__(self, *, allow_network: bool = False, env_file: Path | None = None):
        if not allow_network:
            raise DashScopeError("Real DashScope transport requires explicit network opt-in")
        disable_proxy_environment()
        self.proxy_disabled = not any(
            key.lower().endswith("_proxy") and key.lower() != "no_proxy" for key in os.environ
        )
        self.__key = load_dashscope_key(env_file)

    def __call__(self, payload: dict) -> dict:
        request = urllib.request.Request(
            CHAT_URL,
            data=canonical(payload).encode(),
            headers={
                "Authorization": "Bearer " + self.__key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect()).open(
                request, timeout=90
            ) as response:
                raw = response.read().decode()
            parsed = json.loads(raw)
            if self.__key in raw or self.__key in canonical(parsed):
                raise DashScopeError("Unsafe DashScope response")
            return parsed
        except DashScopeError:
            raise
        except Exception:
            raise DashScopeError("DashScope request failed; response details withheld") from None


class DashScopeChatClient:
    """One-call-at-a-time client with the project's visible telemetry ledger."""

    def __init__(self, transport):
        self.transport = transport
        self.events: list[dict] = []
        self.usage = UsageTracker(on_event=self.events.append)

    def complete(
        self,
        messages: list[dict],
        *,
        phase: str,
        max_tokens: int = 2048,
        synthetic: bool = False,
    ) -> dict:
        if type(max_tokens) is not int or not 1 <= max_tokens <= 131072:
            raise ValueError("Invalid output cap")
        clean_messages = [visible_message(message) for message in messages]
        if any(not isinstance(message.get("content"), str) for message in clean_messages):
            raise ValueError("Messages must have visible text content")
        payload = {
            "model": MODEL,
            "messages": clean_messages,
            "temperature": 0,
            "max_tokens": max_tokens,
            "stream": False,
            "enable_thinking": False,
            "preserve_thinking": False,
        }
        # Reserve the model's documented context ceiling conservatively.  The
        # actual provider-reported count remains the only result used below.
        self.usage.before_call(1_000_000, max_tokens)
        metadata = {
            "call_id": self.usage.new_call_id(),
            "phase": phase,
            "synthetic": synthetic,
        }
        self.usage.emit_event({**metadata, "event": "request", "request": payload})
        started = time.monotonic()
        call = None
        message = None
        try:
            try:
                response = self.transport(payload)
            except KeyboardInterrupt:
                raise
            except Exception:
                raise DashScopeError("DashScope call failed; usage unavailable") from None
            if not isinstance(response, dict):
                raise DashScopeError("DashScope response is invalid")
            call = parse_usage(
                response,
                time.monotonic() - started,
                provider="dashscope",
                requested_model=MODEL,
                **metadata,
            )
            try:
                message = visible_message(response["choices"][0]["message"])
            except Exception:
                raise DashScopeError("Visible DashScope response is invalid") from None
            if not isinstance(message.get("content"), str):
                raise DashScopeError("DashScope response has no visible text")
            self.usage.emit_event({**metadata, "event": "response", "message": message})
        except KeyboardInterrupt:
            raise
        except Exception:
            if call is not None:
                call = replace(call, status="failed", error_category="response_invalid")
            raise
        finally:
            if call is None:
                call = CallUsage(
                    None,
                    None,
                    None,
                    time.monotonic() - started,
                    provider="dashscope",
                    requested_model=MODEL,
                    status="failed_usage_unavailable",
                    accounting_trusted=False,
                    usage_issues=("usage_unavailable",),
                    **metadata,
                )
            try:
                self.usage.record(call)
            except Exception:
                if not isinstance(sys.exc_info()[1], KeyboardInterrupt):
                    raise
        if call is None or not call.accounting_trusted:
            raise DashScopeError("DashScope response has no usable token accounting")
        return message


def _uncached_cost_cny(input_tokens: int, output_tokens: int) -> float:
    """Estimate the published Beijing realtime Qwen3.8-Flash uncached price."""

    return (input_tokens * 0.8 + output_tokens * 2.7) / 1e6


def usage_report(client: DashScopeChatClient) -> dict:
    """Return token telemetry plus an explicitly CNY-denominated estimate."""

    report = client.usage.summary()
    calls = []
    total = 0.0
    cost_known = True
    for call in report["calls"]:
        item = dict(call)
        if (
            item.get("kind") == "generation"
            and type(item.get("input_tokens")) is int
            and type(item.get("output_tokens")) is int
            and not item.get("cached_input_tokens")
        ):
            item["estimated_cost_cny"] = _uncached_cost_cny(
                item["input_tokens"], item["output_tokens"]
            )
            total += item["estimated_cost_cny"]
        else:
            item["estimated_cost_cny"] = None
            if item.get("cached_input_tokens"):
                item["cost_note"] = "cached Qwen3.8 tokens use a console-specific rate"
            cost_known = False
        if item.get("kind") == "generation":
            # CallUsage retains the shared ledger's USD generation invariant;
            # this rendered DashScope report is explicitly CNY-denominated.
            item["currency"] = "CNY"
            item["pricing_source"] = PRICING_SOURCE
        calls.append(item)
    report["calls"] = calls
    report["estimated_cost_usd"] = None
    report["accounted_cost_usd"] = None
    report["estimated_cost_cny"] = total if cost_known else None
    report["accounted_cost_cny"] = total if cost_known else None
    report["usage_status"] = "available" if cost_known else "unavailable"
    report["cost_currency"] = "CNY"
    report["pricing_source"] = PRICING_SOURCE
    report["pricing_basis"] = {
        "region": "Beijing",
        "model": MODEL,
        "input_cny_per_million": 0.8,
        "output_cny_per_million": 2.7,
        "cached_input_rate": "not published; use the Model Studio console",
        "free_allowance_not_deducted": True,
        "source": PRICING_TABLE_SOURCE,
    }
    return report
