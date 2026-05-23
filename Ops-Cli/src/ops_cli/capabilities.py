from __future__ import annotations

import sys
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    platform: str
    command: str
    scenes: tuple[str, ...] = ()
    recovery_policy: str = "interactive_if_tty"
    dry_run_policy: str = "check_only"
    artifact_types: tuple[str, ...] = ()


@dataclass
class SessionRecoveryState:
    required: bool = False
    interactive: bool = False
    scenes_refreshed: list[str] = field(default_factory=list)
    retry_count: int = 0

    def mark_required(self) -> None:
        self.required = True

    def mark_refreshed(self, scene: str) -> None:
        self.required = True
        if scene not in self.scenes_refreshed:
            self.scenes_refreshed.append(scene)
        self.retry_count = max(self.retry_count, 1)

    def as_dict(self) -> dict[str, object]:
        return {
            "required": self.required,
            "interactive": self.interactive,
            "scenes_refreshed": list(self.scenes_refreshed),
            "retry_count": self.retry_count,
        }


@dataclass(frozen=True)
class CapabilityExecution:
    spec: CapabilitySpec
    dry_run: bool
    interactive_login: bool
    allow_recovery: bool
    recovery: SessionRecoveryState


def _spec(
    identifier: str,
    platform: str,
    command: str,
    *,
    scenes: tuple[str, ...] = (),
    recovery_policy: str = "interactive_if_tty",
    artifact_types: tuple[str, ...] = (),
) -> CapabilitySpec:
    return CapabilitySpec(
        id=identifier,
        platform=platform,
        command=command,
        scenes=scenes,
        recovery_policy=recovery_policy,
        artifact_types=artifact_types,
    )


_CAPABILITIES = {
    spec.id: spec
    for spec in (
        _spec("browser.check", "browser", "check", recovery_policy="never"),
        _spec("jst.auth.check", "jst", "auth check", scenes=("order_list",), recovery_policy="never"),
        _spec("jst.auth.ensure", "jst", "auth ensure", scenes=("order_list",)),
        _spec("jst.auth.capture", "jst", "auth capture", scenes=("order_list",), recovery_policy="explicit"),
        _spec("jst.profit.yesterday", "jst", "profit yesterday", scenes=("business_profit_multi_dimension_report",)),
        _spec("jst.profit.learn", "jst", "profit learn", scenes=("business_profit_multi_dimension_report",), recovery_policy="explicit"),
        _spec("jst.profit.month", "jst", "profit month", scenes=("business_profit_multi_dimension_report",)),
        _spec("jst.product.sync", "jst", "product sync", scenes=("product_export",), artifact_types=("xlsx",)),
        _spec("jst.product.learn", "jst", "product learn", scenes=("product_export",), recovery_policy="explicit"),
        _spec("jst.browser.learn", "jst", "browser learn", recovery_policy="explicit"),
        _spec("jst.shop-goods.import", "jst", "shop-goods import", scenes=("order_list",), artifact_types=("xlsx",)),
        _spec("jst.order.label", "jst", "order label", scenes=("order_list",)),
        _spec("jst.order.remark", "jst", "order remark", scenes=("order_list",)),
        _spec("jst.order.logistics", "jst", "order logistics", scenes=("order_list", "order_logistics_trace")),
        _spec("jst.order.logistics.learn", "jst", "order logistics learn", scenes=("order_list", "order_logistics_trace"), recovery_policy="explicit"),
        _spec("jst.order.invoice", "jst", "order invoice", scenes=("order_list", "order_invoice_workorder")),
        _spec("jst.order.invoice.learn", "jst", "order invoice learn", scenes=("order_list", "order_invoice_workorder"), recovery_policy="explicit"),
        _spec("jst.order.reimburse", "jst", "order reimburse", scenes=("order_list",), artifact_types=("xlsx",)),
        _spec("jst.order.stats", "jst", "order stats", scenes=("profit_multi_dimension_report",)),
        _spec("jst.order.stats.learn", "jst", "order stats learn", scenes=("profit_multi_dimension_report",), recovery_policy="explicit"),
        _spec("tmcs.auth.check", "tmcs", "auth check", scenes=("maochao_item_search",), recovery_policy="never"),
        _spec("tmcs.auth.ensure", "tmcs", "auth ensure", scenes=("maochao_item_search",)),
        _spec("tmcs.auth.capture", "tmcs", "auth capture", scenes=("maochao_item_search",), recovery_policy="explicit"),
        _spec("tmcs.product.list", "tmcs", "product list", recovery_policy="never"),
        _spec("tmcs.product.sync", "tmcs", "product sync", scenes=("maochao_item_search", "maochao_item_export"), artifact_types=("xlsx",)),
        _spec("tmcs.product.learn", "tmcs", "product learn", scenes=("maochao_item_search", "maochao_item_export"), recovery_policy="explicit"),
        _spec("tmcs.inventory.export", "tmcs", "inventory export", scenes=("maochao_inventory_search", "maochao_inventory_export"), artifact_types=("xlsx",)),
        _spec("tmcs.inventory.learn", "tmcs", "inventory learn", scenes=("maochao_inventory_search", "maochao_inventory_export"), recovery_policy="explicit"),
        _spec("tmcs.inventory.adjust", "tmcs", "inventory adjust", scenes=("maochao_inventory_search",)),
        _spec("tmcs.inventory.adjust-learn", "tmcs", "inventory adjust-learn", scenes=("maochao_inventory_search",), recovery_policy="explicit"),
        _spec("tmcs.stock.query", "tmcs", "stock query", scenes=("maochao_inventory_search",)),
        _spec("tmcs.bill.download", "tmcs", "bill download", scenes=("statement_bill_list_for_supplier", "statement_bill_dynamic_list", "download_file_query"), artifact_types=("xlsx",)),
        _spec("tmcs.bill.learn", "tmcs", "bill learn", scenes=("statement_bill_list_for_supplier", "statement_bill_dynamic_list", "download_file_query"), recovery_policy="explicit"),
        _spec("tmcs.promotion-bill.download", "tmcs", "promotion-bill download", scenes=("tmcs_promotion_zdx_bill_export", "tmcs_promotion_wxt_bill_export", "download_file_query"), artifact_types=("xlsx", "csv")),
        _spec("tmcs.promotion-bill.learn", "tmcs", "promotion-bill learn", scenes=("tmcs_promotion_zdx_bill_export", "tmcs_promotion_wxt_bill_export", "download_file_query"), recovery_policy="explicit"),
        _spec("tmcs.listing.create", "tmcs", "listing create"),
    )
}
_COMMAND_INDEX = {(spec.platform, spec.command): spec for spec in _CAPABILITIES.values()}
_CURRENT_EXECUTION: ContextVar[CapabilityExecution | None] = ContextVar("ops_capability_execution", default=None)


def capability_ids() -> set[str]:
    return set(_CAPABILITIES)


def get_capability(identifier: str) -> CapabilitySpec:
    return _CAPABILITIES[identifier]


def capability_for_command(platform: str, command: str) -> CapabilitySpec:
    return _COMMAND_INDEX[(platform, command)]


def current_capability_execution() -> CapabilityExecution | None:
    return _CURRENT_EXECUTION.get()


def require_interactive_recovery(scene: str) -> None:
    execution = current_capability_execution()
    if execution is not None and not execution.allow_recovery:
        execution.recovery.mark_required()
        raise RuntimeError(f"session 不可用：{scene} 需要交互登录恢复，当前执行模式禁止自动恢复。")


def mark_scene_refreshed(scene: str) -> None:
    execution = current_capability_execution()
    if execution is not None:
        execution.recovery.mark_refreshed(scene)


def recovery_must_fail_fast() -> bool:
    execution = current_capability_execution()
    return bool(execution is not None and not execution.dry_run and not execution.allow_recovery)


def _interactive_default() -> bool:
    return bool(sys.stdin.isatty())


@contextmanager
def bind_capability_execution(
    spec: CapabilitySpec,
    *,
    dry_run: bool = False,
    interactive_login: bool | None = None,
) -> Iterator[CapabilityExecution]:
    interactive = _interactive_default() if interactive_login is None else interactive_login
    allow_recovery = (
        not dry_run
        and interactive
        and spec.recovery_policy in {"interactive_if_tty", "explicit"}
    )
    recovery = SessionRecoveryState(interactive=allow_recovery)
    execution = CapabilityExecution(
        spec=spec,
        dry_run=dry_run,
        interactive_login=interactive,
        allow_recovery=allow_recovery,
        recovery=recovery,
    )
    token = _CURRENT_EXECUTION.set(execution)
    try:
        yield execution
    finally:
        _CURRENT_EXECUTION.reset(token)
