from datetime import datetime
from typing import Any, Callable

import typer

from ops_cli.browser import check_browser_port
from ops_cli.capabilities import capability_for_command
from ops_cli.config import get_config
from ops_cli.execution import capability_failure_response, run_capability
from ops_cli.logger import log_command, setup_logger
from ops_cli.output import CommandResponse, emit_response
from ops_cli.platforms.jst.auth import check_auth as jst_check_auth
from ops_cli.platforms.jst.auth import capture_auth as jst_capture_auth
from ops_cli.platforms.jst.auth import ensure_auth as jst_ensure_auth
from ops_cli.platforms.jst.browser import learn_jst_browser_scene
from ops_cli.platforms.jst.invoice import DEFAULT_INVOICE_TYPE
from ops_cli.platforms.jst.invoice import DEFAULT_QUANTITY
from ops_cli.platforms.jst.invoice import learn_order_invoice_workorder as learn_jst_order_invoice_workorder
from ops_cli.platforms.jst.invoice import run_order_invoice_workorder as run_jst_order_invoice_workorder
from ops_cli.platforms.jst.order import DEFAULT_LABELS
from ops_cli.platforms.jst.order import DEFAULT_REMARK_TEXT
from ops_cli.platforms.jst.order import learn_order_logistics as learn_jst_order_logistics
from ops_cli.platforms.jst.order import run_order_logistics as run_jst_order_logistics
from ops_cli.platforms.jst.order import run_order_label as run_jst_order_label
from ops_cli.platforms.jst.order import run_order_remark as run_jst_order_remark
from ops_cli.platforms.jst.pickup_watch import run_pickup_watch as run_jst_pickup_watch
from ops_cli.platforms.jst.profit import get_month_profit, learn_jst_profit_scene
from ops_cli.platforms.jst.profit import run_yesterday_profit as run_jst_profit_yesterday
from ops_cli.platforms.jst.product import learn_jst_product_sync
from ops_cli.platforms.jst.product import run_product_sync as run_jst_product_sync
from ops_cli.platforms.jst.reimburse import run_order_reimburse_workorder as run_jst_order_reimburse_workorder
from ops_cli.platforms.jst.shop_goods import import_jst_shop_goods
from ops_cli.platforms.jst.stats import learn_order_stats as learn_jst_order_stats
from ops_cli.platforms.jst.stats import run_order_stats as run_jst_order_stats
from ops_cli.platforms.tmcs.auth import check_auth as tmcs_check_auth
from ops_cli.platforms.tmcs.auth import capture_auth as tmcs_capture_auth
from ops_cli.platforms.tmcs.auth import ensure_auth as tmcs_ensure_auth
from ops_cli.platforms.tmcs.bill import learn_bill_download as learn_tmcs_bill_download
from ops_cli.platforms.tmcs.bill import run_bill_download as run_tmcs_bill_download
from ops_cli.platforms.tmcs.inventory import learn_inventory_adjust as learn_tmcs_inventory_adjust
from ops_cli.platforms.tmcs.inventory import learn_inventory_export as learn_tmcs_inventory_export
from ops_cli.platforms.tmcs.inventory import run_inventory_adjust as run_tmcs_inventory_adjust
from ops_cli.platforms.tmcs.inventory import run_inventory_export as run_tmcs_inventory_export
from ops_cli.platforms.tmcs.listing import create_listing as tmcs_create_listing
from ops_cli.platforms.tmcs.promotion_bill import learn_promotion_bill as learn_tmcs_promotion_bill
from ops_cli.platforms.tmcs.promotion_bill import run_promotion_bill_download as run_tmcs_promotion_bill_download
from ops_cli.platforms.tmcs.product import learn_product_sync as learn_tmcs_product_sync
from ops_cli.platforms.tmcs.product import run_product_sync as run_tmcs_product_sync
from ops_cli.platforms.tmcs.product import list_products as tmcs_list_products
from ops_cli.platforms.tmcs.stock import query_stock as query_tmcs_stock


app = typer.Typer(help="Ecommerce operations CLI.", no_args_is_help=True)
browser_app = typer.Typer(help="Browser utility commands.", no_args_is_help=True)
jst_app = typer.Typer(help="Jushuitan platform commands.", no_args_is_help=True)
tmcs_app = typer.Typer(help="Tmall Chaoshi platform commands.", no_args_is_help=True)
jst_auth_app = typer.Typer(help="JST auth commands.", no_args_is_help=True)
jst_profit_app = typer.Typer(help="JST profit commands.", no_args_is_help=True)
jst_product_app = typer.Typer(help="JST product commands.", no_args_is_help=True)
jst_browser_app = typer.Typer(help="JST browser learning commands.", no_args_is_help=True)
jst_shop_goods_app = typer.Typer(help="JST shop goods import commands.", no_args_is_help=True)
jst_order_app = typer.Typer(help="JST order commands.", no_args_is_help=True)
jst_order_invoice_app = typer.Typer(help="JST order invoice workorder commands.")
jst_order_logistics_app = typer.Typer(help="JST order logistics commands.")
jst_order_reimburse_app = typer.Typer(help="JST brush reimburse workorder commands.")
jst_order_stats_app = typer.Typer(help="JST order stats commands.")
tmcs_auth_app = typer.Typer(help="TMCS auth commands.", no_args_is_help=True)
tmcs_product_app = typer.Typer(help="TMCS product commands.", no_args_is_help=True)
tmcs_inventory_app = typer.Typer(help="TMCS inventory commands.", no_args_is_help=True)
tmcs_stock_app = typer.Typer(help="TMCS stock query commands.", no_args_is_help=True)
tmcs_bill_app = typer.Typer(help="TMCS bill commands.", no_args_is_help=True)
tmcs_promotion_bill_app = typer.Typer(help="TMCS promotion bill commands.", no_args_is_help=True)
tmcs_listing_app = typer.Typer(help="TMCS listing commands.", no_args_is_help=True)


def _get_json_flag(ctx: typer.Context) -> bool:
    return bool((ctx.obj or {}).get("json_output", False))


def _execute(
    ctx: typer.Context,
    *,
    command_name: str,
    params: dict[str, Any],
    handler: Callable[[], CommandResponse],
    force_json: bool = False,
) -> None:
    setup_logger()
    get_config()
    started_at = datetime.now().isoformat(timespec="seconds")
    command_parts = command_name.split()
    platform = command_parts[1]
    command = " ".join(command_parts[2:])
    spec = capability_for_command(platform, command)
    interactive_login = (ctx.obj or {}).get("interactive_login")
    try:
        response = run_capability(
            spec=spec,
            params=params,
            handler=handler,
            interactive_login=interactive_login,
        )
    except Exception as exc:
        response = capability_failure_response(
            spec=spec,
            params=params,
            exc=exc,
            interactive_login=interactive_login,
        )
        emit_response(response, as_json=_get_json_flag(ctx) or force_json)
        log_command(
            {
                "timestamp": started_at,
                "command": command_name,
                "params": params,
                "result": response.model_dump(),
            }
        )
        raise typer.Exit(code=1)

    emit_response(response, as_json=_get_json_flag(ctx) or force_json)
    log_command(
        {
            "timestamp": started_at,
            "command": command_name,
            "params": params,
            "result": response.model_dump(),
        }
    )


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    interactive_login: bool | None = typer.Option(
        None,
        "--interactive-login/--no-interactive-login",
        help="Override terminal detection for SessionHub login recovery.",
    ),
) -> None:
    ctx.obj = {"json_output": json_output, "interactive_login": interactive_login}


@browser_app.command("check")
def browser_check(
    ctx: typer.Context,
    port: int = typer.Option(9222, "--port", help="Chrome remote debugging port."),
) -> None:
    _execute(ctx, command_name="ops browser check", params={"port": port}, handler=lambda: check_browser_port(port))


@jst_auth_app.command("check")
def jst_auth_check(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops jst auth check", params={}, handler=jst_check_auth)


@jst_auth_app.command("ensure")
def jst_auth_ensure(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops jst auth ensure", params={}, handler=jst_ensure_auth)


@jst_auth_app.command("capture")
def jst_auth_capture(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops jst auth capture", params={}, handler=jst_capture_auth)


@jst_profit_app.command("yesterday")
def jst_profit_yesterday(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops jst profit yesterday", params={}, handler=run_jst_profit_yesterday)


@jst_profit_app.command("learn")
def jst_profit_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst profit learn",
        params={"force": force},
        handler=lambda: learn_jst_profit_scene(force=force),
    )


@jst_profit_app.command("month")
def jst_profit_month(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops jst profit month", params={}, handler=get_month_profit)


@jst_product_app.command("sync", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def jst_product_sync(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, do not download or overwrite."),
    use_local_only: bool = typer.Option(False, "--use-local-only", help="Skip backend export and use the local Downloads file."),
    keep_brands: str | None = typer.Option(None, "--keep-brands", help="Brands to keep. Accepts one or more values."),
) -> None:
    keep_brand_values = [keep_brands] if keep_brands else []
    keep_brand_values.extend(arg for arg in ctx.args if not str(arg).startswith("-"))
    _execute(
        ctx,
        command_name="ops jst product sync",
        params={"dry_run": dry_run, "use_local_only": use_local_only, "keep_brands": keep_brand_values},
        handler=lambda: run_jst_product_sync(
            dry_run=dry_run,
            use_local_only=use_local_only,
            keep_brands=keep_brand_values or None,
        ),
    )


@jst_product_app.command("learn")
def jst_product_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst product learn",
        params={"force": force},
        handler=lambda: learn_jst_product_sync(force=force),
    )


@jst_browser_app.command("learn")
def jst_browser_learn(
    ctx: typer.Context,
    scene: str = typer.Option(..., "--scene", help="JST browser scene name, for example shop-goods-import."),
    timeout: int = typer.Option(90, "--timeout", help="Seconds to wait while user manually completes the page flow in primary Chrome."),
    cdp_url: str | None = typer.Option(None, "--cdp-url", help="Primary Chrome CDP URL. Do not use 9222 here."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst browser learn",
        params={"scene": scene, "timeout": timeout, "cdp_url": cdp_url},
        handler=lambda: learn_jst_browser_scene(scene=scene, timeout=timeout, cdp_url=cdp_url),
    )


@jst_shop_goods_app.command("import")
def jst_shop_goods_import(
    ctx: typer.Context,
    file_path: str = typer.Option(..., "--file", help="Path to JST shop goods import xlsx."),
    shop_name: str = typer.Option("（猫超）启明工贸有限公司", "--shop-name", help="JST shop name."),
    mode: str = typer.Option("ignore", "--mode", help="Import mode: ignore or cover."),
    output: str = typer.Option("json", "--output", help="Output format. Currently only json is supported."),
) -> None:
    if output.lower() != "json":
        raise typer.BadParameter("当前仅支持 --output json。")
    _execute(
        ctx,
        command_name="ops jst shop-goods import",
        params={"file": file_path, "shop_name": shop_name, "mode": mode, "output": output},
        handler=lambda: import_jst_shop_goods(file_path=file_path, shop_name=shop_name, mode=mode),
    )


@jst_order_app.command("label")
def jst_order_label(
    ctx: typer.Context,
    order_id: list[str] = typer.Option(None, "--order-id", help="Order ID. Repeatable."),
    input_path: str | None = typer.Option(None, "--input", help="Order JSON file with orders[]."),
    limit: int | None = typer.Option(None, "--limit", help="Only process the first N orders."),
    execute: bool = typer.Option(False, "--execute", help="Actually write remark and labels."),
    label: str = typer.Option(DEFAULT_LABELS, "--label", help="Labels text."),
    remark_text: str = typer.Option(DEFAULT_REMARK_TEXT, "--remark-text", help="Remark text."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst order label",
        params={
            "order_ids": order_id,
            "input_path": input_path,
            "limit": limit,
            "execute": execute,
            "labels": label,
            "remark_text": remark_text,
        },
        handler=lambda: run_jst_order_label(
            order_ids=order_id,
            input_path=input_path,
            limit=limit,
            execute=execute,
            labels=label,
            remark_text=remark_text,
        ),
    )


@jst_order_app.command("remark")
def jst_order_remark(
    ctx: typer.Context,
    order_id: list[str] = typer.Option(None, "--order-id", help="Order ID. Repeatable."),
    input_path: str | None = typer.Option(None, "--input", help="Order JSON file with orders[]."),
    limit: int | None = typer.Option(None, "--limit", help="Only process the first N orders."),
    execute: bool = typer.Option(False, "--execute", help="Actually write seller remark."),
    remark_text: str = typer.Option(..., "--remark-text", help="Seller remark text."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst order remark",
        params={
            "order_ids": order_id,
            "input_path": input_path,
            "limit": limit,
            "execute": execute,
            "remark_text": remark_text,
        },
        handler=lambda: run_jst_order_remark(
            order_ids=order_id,
            input_path=input_path,
            limit=limit,
            execute=execute,
            remark_text=remark_text,
        ),
    )


@jst_order_app.command("pickup-watch")
def jst_order_pickup_watch(
    ctx: typer.Context,
    hours: int = typer.Option(48, "--hours", help="Lookback hours for paid orders."),
    shop_name: str | None = typer.Option(None, "--shop-name", help="Optional JST shop name filter."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use representative local sample orders only."),
    debug: bool = typer.Option(False, "--debug", help="Include platform debugging diagnostics when supported."),
    output: str = typer.Option("json", "--output", help="Output format. Currently only json is supported."),
) -> None:
    if output.lower() != "json":
        raise typer.BadParameter("当前仅支持 --output json。")
    _execute(
        ctx,
        command_name="ops jst order pickup-watch",
        params={
            "hours": hours,
            "shop_name": shop_name,
            "dry_run": dry_run,
            "debug": debug,
            "output": output,
        },
        handler=lambda: run_jst_pickup_watch(hours=hours, shop_name=shop_name, dry_run=dry_run, debug=debug),
        force_json=True,
    )


@jst_order_logistics_app.callback(invoke_without_command=True)
def jst_order_logistics(
    ctx: typer.Context,
    order_id: list[str] = typer.Option(None, "--order-id", help="JST order number. Repeatable."),
    outer_order_id: list[str] = typer.Option(None, "--outer-order-id", help="External platform order number. Repeatable."),
    input_path: str | None = typer.Option(None, "--input", help="Order input file. Supports JSON/TXT/CSV."),
    limit: int | None = typer.Option(None, "--limit", help="Only query the first N orders."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _execute(
        ctx,
        command_name="ops jst order logistics",
        params={
            "order_ids": order_id,
            "outer_order_ids": outer_order_id,
            "input_path": input_path,
            "limit": limit,
        },
        handler=lambda: run_jst_order_logistics(
            order_ids=order_id,
            outer_order_ids=outer_order_id,
            input_path=input_path,
            limit=limit,
        ),
    )


@jst_order_logistics_app.command("learn")
def jst_order_logistics_learn(
    ctx: typer.Context,
    order_id: str | None = typer.Option(None, "--order-id", help="JST order number used to trigger logistics panel."),
    outer_order_id: str | None = typer.Option(None, "--outer-order-id", help="External order number used to trigger logistics panel."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst order logistics learn",
        params={"order_id": order_id, "outer_order_id": outer_order_id},
        handler=lambda: learn_jst_order_logistics(order_id=order_id, outer_order_id=outer_order_id),
    )


@jst_order_invoice_app.callback(invoke_without_command=True)
def jst_order_invoice(
    ctx: typer.Context,
    order_id: str | None = typer.Option(None, "--order-id", help="JST order number or platform order number."),
    outer_order_id: str | None = typer.Option(None, "--outer-order-id", help="External platform order number."),
    invoice_type: str = typer.Option(DEFAULT_INVOICE_TYPE, "--invoice-type", help="Invoice type. Default: 专用发票."),
    title: str | None = typer.Option(None, "--title", help="Invoice title."),
    tax_no: str | None = typer.Option(None, "--tax-no", help="Tax number."),
    address: str | None = typer.Option(None, "--address", help="Company address for special VAT invoice."),
    phone: str | None = typer.Option(None, "--phone", help="Company phone for special VAT invoice."),
    bank: str | None = typer.Option(None, "--bank", help="Bank name for special VAT invoice."),
    bank_account: str | None = typer.Option(None, "--bank-account", help="Bank account for special VAT invoice."),
    amount: str | None = typer.Option(None, "--amount", help="Invoice amount."),
    quantity: int = typer.Option(DEFAULT_QUANTITY, "--quantity", help="Product quantity."),
    execute: bool = typer.Option(False, "--execute", help="Actually create invoice workorder."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _execute(
        ctx,
        command_name="ops jst order invoice",
        params={
            "order_id": order_id,
            "outer_order_id": outer_order_id,
            "invoice_type": invoice_type,
            "title": title,
            "tax_no": tax_no,
            "address": address,
            "phone": phone,
            "bank": bank,
            "bank_account": bank_account,
            "amount": amount,
            "quantity": quantity,
            "execute": execute,
        },
        handler=lambda: run_jst_order_invoice_workorder(
            order_id=order_id or "",
            outer_order_id=outer_order_id,
            invoice_type=invoice_type,
            title=title or "",
            tax_no=tax_no or "",
            address=address or "",
            phone=phone or "",
            bank=bank or "",
            bank_account=bank_account or "",
            amount=amount or "",
            quantity=quantity,
            execute=execute,
        ),
    )


@jst_order_invoice_app.command("learn")
def jst_order_invoice_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst order invoice learn",
        params={"force": force},
        handler=lambda: learn_jst_order_invoice_workorder(force=force),
    )


@jst_order_reimburse_app.callback(invoke_without_command=True)
def jst_order_reimburse(
    ctx: typer.Context,
    outer_order_id: str = typer.Option(..., "--outer-order-id", help="External platform order number."),
    principal_total: str = typer.Option(..., "--principal-total", help="Brush order principal total."),
    payout_total: str = typer.Option(..., "--payout-total", help="Brush commission payout total."),
    product_code: str = typer.Option(..., "--product-code", help="Product code for workorder field."),
    product_name: str = typer.Option("", "--product-name", help="Product name fallback for workorder field."),
    workbook_file: str = typer.Option("", "--workbook-file", help="Workbook file to upload when executing."),
    execute: bool = typer.Option(False, "--execute", help="Upload workbook and create reimburse workorder."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _execute(
        ctx,
        command_name="ops jst order reimburse",
        params={
            "outer_order_id": outer_order_id,
            "principal_total": principal_total,
            "payout_total": payout_total,
            "product_code": product_code,
            "product_name": product_name,
            "workbook_file": workbook_file,
            "execute": execute,
        },
        handler=lambda: run_jst_order_reimburse_workorder(
            outer_order_id=outer_order_id,
            principal_total=principal_total,
            payout_total=payout_total,
            product_code=product_code,
            product_name=product_name,
            workbook_file=workbook_file,
            execute=execute,
        ),
    )


@jst_order_stats_app.callback(invoke_without_command=True)
def jst_order_stats(
    ctx: typer.Context,
    date_value: str = typer.Option("today", "--date", help="today or YYYY-MM-DD."),
    store: str | None = typer.Option(None, "--store", help="Store name override."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _execute(
        ctx,
        command_name="ops jst order stats",
        params={"date": date_value, "store": store},
        handler=lambda: run_jst_order_stats(date_arg=date_value, store=store),
    )


@jst_order_stats_app.command("learn")
def jst_order_stats_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops jst order stats learn",
        params={"force": force},
        handler=lambda: learn_jst_order_stats(force=force),
    )


@tmcs_auth_app.command("check")
def tmcs_auth_check(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops tmcs auth check", params={}, handler=tmcs_check_auth)


@tmcs_auth_app.command("ensure")
def tmcs_auth_ensure(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops tmcs auth ensure", params={}, handler=tmcs_ensure_auth)


@tmcs_auth_app.command("capture")
def tmcs_auth_capture(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops tmcs auth capture", params={}, handler=tmcs_capture_auth)


@tmcs_product_app.command("list")
def tmcs_product_list(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops tmcs product list", params={}, handler=tmcs_list_products)


@tmcs_product_app.command("sync")
def tmcs_product_sync(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, do not write latest workbook."),
    use_local_only: bool = typer.Option(False, "--use-local-only", help="Skip backend export and use local import file only."),
    force_refresh: bool = typer.Option(False, "--force-refresh", help="Force refresh from TMCS backend export."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs product sync",
        params={"dry_run": dry_run, "use_local_only": use_local_only, "force_refresh": force_refresh},
        handler=lambda: run_tmcs_product_sync(
            dry_run=dry_run,
            use_local_only=use_local_only,
            force_refresh=force_refresh,
        ),
    )


@tmcs_product_app.command("learn")
def tmcs_product_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs product learn",
        params={"force": force},
        handler=lambda: learn_tmcs_product_sync(force=force),
    )


@tmcs_inventory_app.command("export")
def tmcs_inventory_export(
    ctx: typer.Context,
    warehouse_code: str = typer.Option("mc_aokesi_suolong", "--warehouse-code", help="Merchant warehouse code."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, do not download files."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs inventory export",
        params={"warehouse_code": warehouse_code, "dry_run": dry_run},
        handler=lambda: run_tmcs_inventory_export(warehouse_code=warehouse_code, dry_run=dry_run),
    )


@tmcs_inventory_app.command("learn")
def tmcs_inventory_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs inventory learn",
        params={"force": force},
        handler=lambda: learn_tmcs_inventory_export(force=force),
    )


@tmcs_inventory_app.command("adjust", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def tmcs_inventory_adjust(
    ctx: typer.Context,
    action: str = typer.Option(..., "--action", help="increase, decrease, or clear."),
    sku_id: str | None = typer.Option(None, "--sku-id", help="Platform SKU ID."),
    item_id: str | None = typer.Option(None, "--item-id", help="Platform item ID."),
    quantity: int | None = typer.Option(None, "--quantity", help="Quantity for increase/decrease."),
    sku_adjust: list[str] | None = typer.Option(None, "--sku-adjust", help="Batch SKU:quantity item. Repeatable."),
    warehouse_code: str = typer.Option("mc_aokesi_suolong", "--warehouse-code", help="Merchant warehouse code."),
    execute: bool = typer.Option(False, "--execute", help="Actually submit inventory adjustment."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs inventory adjust",
        params={
            "action": action,
            "sku_id": sku_id,
            "item_id": item_id,
            "quantity": quantity,
            "sku_adjust": sku_adjust or [],
            "warehouse_code": warehouse_code,
            "execute": execute,
        },
        handler=lambda: run_tmcs_inventory_adjust(
            action=action,
            sku_id=sku_id,
            item_id=item_id,
            quantity=quantity,
            sku_adjust=sku_adjust or [],
            warehouse_code=warehouse_code,
            execute=execute,
        ),
    )


@tmcs_inventory_app.command("adjust-learn")
def tmcs_inventory_adjust_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs inventory adjust-learn",
        params={"force": force},
        handler=lambda: learn_tmcs_inventory_adjust(force=force),
    )


@tmcs_stock_app.command("query")
def tmcs_stock_query(
    ctx: typer.Context,
    item_ids: str = typer.Option(..., "--item-ids", help="Comma-separated TMCS platform item IDs."),
    warehouse_code: str = typer.Option("mc_aokesi_suolong", "--warehouse-code", help="TMCS merchant warehouse code."),
    output: str = typer.Option("json", "--output", help="Output format. Currently only json is supported."),
) -> None:
    def handler() -> CommandResponse:
        if output.lower() != "json":
            raise RuntimeError("tmcs stock query 当前仅支持 --output json。")
        return CommandResponse(
            success=True,
            platform="tmcs",
            command="stock query",
            data={"rows": query_tmcs_stock(item_ids=item_ids, warehouse_code=warehouse_code)},
        )

    _execute(
        ctx,
        command_name="ops tmcs stock query",
        params={"item_ids": item_ids, "warehouse_code": warehouse_code, "output": output},
        handler=handler,
        force_json=True,
    )


@tmcs_bill_app.command("download")
def tmcs_bill_download(
    ctx: typer.Context,
    start: str | None = typer.Option(None, "--start", help="Start date in YYYY-MM-DD."),
    end: str | None = typer.Option(None, "--end", help="End date in YYYY-MM-DD."),
    last_month: bool = typer.Option(False, "--last-month", help="Download previous month's bills, querying through month-end + 3 days."),
    download_statement_list: bool = typer.Option(False, "--download-statement-list", help="Also download 对账单列表.xlsx."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, do not download files."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs bill download",
        params={
            "start": start,
            "end": end,
            "last_month": last_month,
            "download_statement_list": download_statement_list,
            "dry_run": dry_run,
        },
        handler=lambda: run_tmcs_bill_download(
            start=start,
            end=end,
            last_month=last_month,
            download_statement_list=download_statement_list,
            dry_run=dry_run,
        ),
    )


@tmcs_bill_app.command("learn")
def tmcs_bill_learn(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs bill learn",
        params={"force": force},
        handler=lambda: learn_tmcs_bill_download(force=force),
    )


@tmcs_promotion_bill_app.command("download")
def tmcs_promotion_bill_download(
    ctx: typer.Context,
    source: str = typer.Option("all", "--source", help="all, zdx, or wxt."),
    start: str | None = typer.Option(None, "--start", help="Start date in YYYY-MM-DD."),
    end: str | None = typer.Option(None, "--end", help="End date in YYYY-MM-DD."),
    last_month: bool = typer.Option(False, "--last-month", help="Download previous natural month's promotion bills."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, do not download files."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs promotion-bill download",
        params={"source": source, "start": start, "end": end, "last_month": last_month, "dry_run": dry_run},
        handler=lambda: run_tmcs_promotion_bill_download(
            source=source,
            start=start,
            end=end,
            last_month=last_month,
            dry_run=dry_run,
        ),
    )


@tmcs_promotion_bill_app.command("learn")
def tmcs_promotion_bill_learn(
    ctx: typer.Context,
    source: str = typer.Option("all", "--source", help="all, zdx, or wxt."),
    force: bool = typer.Option(False, "--force", help="Force recapture even if scene exists."),
    timeout: int = typer.Option(90, "--timeout", help="Seconds to wait for primary Chrome export request capture."),
) -> None:
    _execute(
        ctx,
        command_name="ops tmcs promotion-bill learn",
        params={"source": source, "force": force, "timeout": timeout},
        handler=lambda: learn_tmcs_promotion_bill(source=source, force=force, timeout=timeout),
    )


@tmcs_listing_app.command("create")
def tmcs_listing_create(ctx: typer.Context) -> None:
    _execute(ctx, command_name="ops tmcs listing create", params={}, handler=tmcs_create_listing)


jst_app.add_typer(jst_auth_app, name="auth")
jst_app.add_typer(jst_profit_app, name="profit")
jst_app.add_typer(jst_product_app, name="product")
jst_app.add_typer(jst_browser_app, name="browser")
jst_app.add_typer(jst_shop_goods_app, name="shop-goods")
jst_app.add_typer(jst_order_app, name="order")
jst_order_app.add_typer(jst_order_invoice_app, name="invoice")
jst_order_app.add_typer(jst_order_logistics_app, name="logistics")
jst_order_app.add_typer(jst_order_reimburse_app, name="reimburse")
jst_order_app.add_typer(jst_order_stats_app, name="stats")
tmcs_app.add_typer(tmcs_auth_app, name="auth")
tmcs_app.add_typer(tmcs_product_app, name="product")
tmcs_app.add_typer(tmcs_inventory_app, name="inventory")
tmcs_app.add_typer(tmcs_stock_app, name="stock")
tmcs_app.add_typer(tmcs_bill_app, name="bill")
tmcs_app.add_typer(tmcs_promotion_bill_app, name="promotion-bill")
tmcs_app.add_typer(tmcs_listing_app, name="listing")
app.add_typer(browser_app, name="browser")
app.add_typer(jst_app, name="jst")
app.add_typer(tmcs_app, name="tmcs")


def main() -> None:
    app()
