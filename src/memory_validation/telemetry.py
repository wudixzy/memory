"""Per-call accounting and conservative pre-call reservations; no output caching."""

from __future__ import annotations

import math
import uuid
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PriceTable:
    version: str = "project-budget-2026-09-11-peak-estimate"
    source: str = "docs/02_compute_budget.md (planning estimate; not live billing)"
    cache_hit_per_million: float = 0.014
    cache_miss_per_million: float = 0.44
    output_per_million: float = 1.32

    def __post_init__(self):
        rates = (self.cache_hit_per_million, self.cache_miss_per_million, self.output_per_million)
        if any(not math.isfinite(rate) or rate < 0 for rate in rates):
            raise ValueError("Invalid pricing rate")

    def estimate(self, input_tokens: int, cached: int, output: int) -> float:
        return (
            cached * self.cache_hit_per_million
            + (input_tokens - cached) * self.cache_miss_per_million
            + output * self.output_per_million
        ) / 1_000_000


@dataclass(frozen=True)
class CallUsage:
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    latency_seconds: float
    retry_count: int = 0
    provider: str = "deepseek"
    requested_model: str = "deepseek-v4-flash"
    resolved_model: str | None = None
    thinking: bool = False
    provider_reported_cost_usd: float | None = None
    status: str = "completed"
    call_id: str | None = None
    phase: str = "unspecified"
    synthetic: bool = False
    accounting_trusted: bool = True
    usage_issues: tuple[str, ...] = ()
    kind: str = "generation"
    input_count: int | None = None
    estimated_cost_cny: float | None = None
    currency: str = "USD"
    pricing_source: str | None = None
    token_usage_trusted: bool | None = None
    error_category: str | None = None

    def __post_init__(self):
        if self.kind not in ("generation", "embedding") or self.currency != (
            "CNY" if self.kind == "embedding" else "USD"
        ):
            raise ValueError("Invalid call kind/currency")
        if self.input_count is not None and (
            type(self.input_count) is not int or self.input_count < 1
        ):
            raise ValueError("Invalid embedding input count")
        for value in (
            self.input_tokens,
            self.output_tokens,
            self.cached_input_tokens,
            self.retry_count,
        ):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Invalid token/retry count")
        if (
            self.cached_input_tokens is not None
            and self.input_tokens is not None
            and self.cached_input_tokens > self.input_tokens
        ):
            raise ValueError("Cached tokens exceed input tokens")
        for value in (
            self.latency_seconds,
            self.provider_reported_cost_usd,
            self.estimated_cost_cny,
        ):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError("Invalid latency/cost")


@dataclass(frozen=True)
class Budget:
    max_calls_per_task: int | None = None
    max_calls_per_run: int | None = None
    max_input_tokens_per_task: int | None = None
    max_output_tokens_per_task: int | None = None
    max_cost_usd_per_task: float | None = None
    max_cost_usd_per_run: float | None = None
    max_cost_cny_per_task: float | None = None
    max_cost_cny_per_run: float | None = None

    def __post_init__(self):
        if any(v is not None and (not math.isfinite(v) or v < 0) for v in asdict(self).values()):
            raise ValueError("Invalid budget")


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class RunLedger:
    cost_usd: float = 0
    uncertain: bool = False
    cost_cny: float = 0
    calls: int = 0


class UsageTracker:
    def __init__(
        self,
        budget: Budget = Budget(),
        ledger: RunLedger | None = None,
        prices: PriceTable = PriceTable(),
        on_change=None,
        on_event=None,
    ):
        self.budget, self.prices = budget, prices
        self.ledger = ledger if ledger is not None else RunLedger()
        self.calls: list[CallUsage] = []
        self.on_change = on_change
        self.on_event = on_event

    def new_call_id(self) -> str:
        return uuid.uuid4().hex

    def emit_event(self, event: dict):
        if self.on_event is not None:
            self.on_event(event)

    def summary(self) -> dict:
        def total(name, calls=None):
            values = [getattr(call, name) for call in (self.calls if calls is None else calls)]
            return None if any(v is None for v in values) else sum(values)

        estimated = 0.0
        accounted = 0.0
        for call in self.calls:
            if call.kind == "embedding":
                continue
            if not call.accounting_trusted:
                estimated = accounted = None
                continue
            if call.input_tokens is None or call.output_tokens is None:
                estimated = None
                if call.provider_reported_cost_usd is None:
                    accounted = None
                elif accounted is not None:
                    accounted += call.provider_reported_cost_usd
                continue
            cost = self.prices.estimate(
                call.input_tokens, call.cached_input_tokens or 0, call.output_tokens
            )
            if estimated is not None:
                estimated += cost
            if accounted is not None:
                accounted += (
                    call.provider_reported_cost_usd
                    if call.provider_reported_cost_usd is not None
                    else cost
                )
        return {
            "llm_calls": sum(c.kind == "generation" for c in self.calls),
            "embedding_calls": sum(c.kind == "embedding" for c in self.calls),
            "total_calls": len(self.calls),
            "accounted_cost_cny": self.cny_total(),
            "input_tokens": total("input_tokens"),
            "output_tokens": total("output_tokens"),
            "cached_input_tokens": total("cached_input_tokens"),
            "latency_seconds": total("latency_seconds"),
            "retry_count": total("retry_count"),
            "provider_reported_cost_usd": total(
                "provider_reported_cost_usd", [c for c in self.calls if c.currency == "USD"]
            ),
            "estimated_cost_usd": estimated,
            "accounted_cost_usd": accounted,
            "usage_status": "unavailable"
            if accounted is None or self.cny_total() is None
            else "available",
            "price_table": asdict(self.prices),
            "calls": [asdict(call) for call in self.calls],
        }

    def cny_total(self):
        calls = [c for c in self.calls if c.kind == "embedding"]
        if any(not c.accounting_trusted or c.estimated_cost_cny is None for c in calls):
            return None
        return sum(c.estimated_cost_cny for c in calls)

    def before_call(self, input_upper_bound: int, output_upper_bound: int, *, embedding_cny=None):
        if embedding_cny is not None and (
            type(embedding_cny) not in (int, float)
            or not math.isfinite(embedding_cny)
            or embedding_cny < 0
        ):
            raise ValueError("Invalid CNY reservation")
        if any(
            type(value) is not int or value < 0 for value in (input_upper_bound, output_upper_bound)
        ):
            raise ValueError("Invalid reservation")
        summary = self.summary()
        if self.ledger.uncertain or any(
            summary[k] is None
            for k in ("input_tokens", "output_tokens", "accounted_cost_usd", "accounted_cost_cny")
        ):
            raise BudgetExceeded("Unknown prior usage; further calls blocked")
        reserve = (
            self.prices.estimate(input_upper_bound, 0, output_upper_bound)
            if embedding_cny is None
            else 0
        )
        cny_reserve = 0 if embedding_cny is None else embedding_cny
        checks = [
            (summary["total_calls"] + 1, self.budget.max_calls_per_task),
            (self.ledger.calls + 1, self.budget.max_calls_per_run),
            (summary["input_tokens"] + input_upper_bound, self.budget.max_input_tokens_per_task),
            (summary["output_tokens"] + output_upper_bound, self.budget.max_output_tokens_per_task),
            (summary["accounted_cost_usd"] + reserve, self.budget.max_cost_usd_per_task),
            (self.ledger.cost_usd + reserve, self.budget.max_cost_usd_per_run),
            (self.cny_total() + cny_reserve, self.budget.max_cost_cny_per_task),
            (self.ledger.cost_cny + cny_reserve, self.budget.max_cost_cny_per_run),
        ]
        if any(limit is not None and value > limit for value, limit in checks):
            raise BudgetExceeded("Call reservation exceeds configured budget")

    def record(self, call: CallUsage):
        previous = self.summary()["accounted_cost_usd"]
        self.calls.append(call)
        self.ledger.calls += 1
        if call.kind == "embedding":
            if call.estimated_cost_cny is None or not call.accounting_trusted:
                self.ledger.uncertain = True
            else:
                self.ledger.cost_cny += call.estimated_cost_cny
        current = self.summary()["accounted_cost_usd"]
        if current is None or previous is None or not call.accounting_trusted:
            self.ledger.uncertain = True
        else:
            self.ledger.cost_usd += current - previous
        if self.on_change:
            self.on_change(self.summary())
        # Check actual consumption too: provider usage may exceed reservations.
        summary = self.summary()
        checks = [
            (summary["total_calls"], self.budget.max_calls_per_task),
            (self.ledger.calls, self.budget.max_calls_per_run),
            (summary["input_tokens"], self.budget.max_input_tokens_per_task),
            (summary["output_tokens"], self.budget.max_output_tokens_per_task),
            (current, self.budget.max_cost_usd_per_task),
            (self.ledger.cost_usd, self.budget.max_cost_usd_per_run),
            (self.cny_total(), self.budget.max_cost_cny_per_task),
            (self.ledger.cost_cny, self.budget.max_cost_cny_per_run),
        ]
        if any(
            value is not None and limit is not None and value > limit for value, limit in checks
        ):
            raise BudgetExceeded("Reported usage exceeds configured budget")
