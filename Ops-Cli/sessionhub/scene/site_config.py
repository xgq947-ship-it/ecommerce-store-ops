from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = ROOT / "config" / "sites"


class ConfigError(RuntimeError):
    pass


def _apply_scene_defaults(data: dict[str, Any]) -> dict[str, Any]:
    scenes = data.get("scenes") or {}
    for raw_scene in scenes.values():
        if not isinstance(raw_scene, dict):
            continue
        raw_scene.setdefault("auto_actions", [])
        raw_scene.setdefault("wait_seconds", 90)
        raw_scene.setdefault("capture_retry_limit", 2)
        raw_scene.setdefault("sensitive_artifact_policy", "local_ignored")
    return data


def _fallback_parse_tmall_config(text: str) -> dict[str, Any]:
    """Small fallback so basic commands still work before PyYAML is installed."""
    data: dict[str, Any] = {
        "site": "tmall_chaoshi",
        "name": "天猫超市商家仓后台",
        "login_url": "",
        "home_url": "",
        "download_manage_url": "",
        "scenes": {
            "download_file_query": {
                "target_url": "https://web.txcs.tmall.com/?frameUrl=https%3A%2F%2Fweb.txcs.tmall.com%2Friver%2Fapp%2Fsettlement_download%2Fentities%2FDownloadFile%2Fquery#745319.745451.745563#745319.745451.745563",
                "match_url_contains": ["DownloadFile", "_m=query"],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "reload"},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "statement_bill_dynamic_list": {
                "target_url": "https://web.txcs.tmall.com/pages/chaoshi/settlement_confirm_query_list?_c_lang=zh-cn&iframeContainerFrom=tm&__IFRAME_CONTAINER_IFRAME_ID__=2",
                "match_url_contains": [
                    "tools.cbbs.tmall.com/gei/export/task/wdk-finance-statement-bill-dynamic-list"
                ],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_text", "text": "查询"},
                    {"type": "click_text", "text": "导出列表"},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "statement_bill_list_for_supplier": {
                "target_url": "https://web.txcs.tmall.com/pages/chaoshi/settlement_confirm_query_list?_c_lang=zh-cn&iframeContainerFrom=tm&__IFRAME_CONTAINER_IFRAME_ID__=2",
                "match_url_contains": [
                    "wdksettlement.hemaos.com/statementBill/v3/listForSupplier"
                ],
                "method": "GET",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_text", "text": "查询"},
                    {"type": "reload"},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "maochao_item_search": {
                "target_url": "https://web.txcs.tmall.com/pages/chaoshi/indus_merchandise_item_list_rex_mc?_c_lang=zh-cn&iframeContainerFrom=tm&__IFRAME_CONTAINER_IFRAME_ID__=2",
                "match_url_contains": [
                    "merchandise-mc.cbbs.tmall.com/webapi/merchandise/item/searchItem"
                ],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_any_text", "texts": ["查询", "搜索"]},
                    {"type": "reload"},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "maochao_item_export": {
                "target_url": "https://web.txcs.tmall.com/pages/chaoshi/indus_merchandise_item_list_rex_mc?_c_lang=zh-cn&iframeContainerFrom=tm&__IFRAME_CONTAINER_IFRAME_ID__=2",
                "match_url_contains": ["one-stock-all-tube-adjust-order-log-export"],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_any_text", "texts": ["查询", "搜索"]},
                    {"type": "click_any_text", "texts": ["导出", "导出商品", "导出列表"]},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "maochao_inventory_search": {
                "target_url": "https://web.txcs.tmall.com/pages/chaoshi/indus_half_tube_inventory_management_qtg?_c_lang=zh-cn&iframeContainerFrom=tm&__IFRAME_CONTAINER_IFRAME_ID__=2",
                "match_url_contains": ["aic.cbbs.tmall.com/one-stock/listOneStockAllTubeInventory"],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_any_text", "texts": ["查询", "搜索"]},
                    {"type": "reload"},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "maochao_inventory_export": {
                "target_url": "https://web.txcs.tmall.com/pages/chaoshi/indus_half_tube_inventory_management_qtg?_c_lang=zh-cn&iframeContainerFrom=tm&__IFRAME_CONTAINER_IFRAME_ID__=2",
                "match_url_contains": ["tools.cbbs.tmall.com/gei/export/task/"],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_any_text", "texts": ["查询", "搜索"]},
                    {"type": "click_any_text", "texts": ["导出", "导出列表", "下载"]},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "tmcs_promotion_zdx_bill_export": {
                "target_url": "https://web.txcs.tmall.com/pages/chaoshi/plan_throw_account_admin?_c_lang=zh-cn&iframeContainerFrom=tm&__IFRAME_CONTAINER_IFRAME_ID__=3",
                "match_url_contains": ["/gei/export/task/ad-funds-flow-export"],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_any_text", "texts": ["查询", "搜索"]},
                    {"type": "click_any_text", "texts": ["导出", "导出列表", "下载"]},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "tmcs_promotion_wxt_bill_export": {
                "target_url": "https://web.txcs.tmall.com/",
                "match_url_contains": ["wxt"],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_any_text", "texts": ["查询", "搜索"]},
                    {"type": "click_any_text", "texts": ["导出", "导出列表", "下载"]},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
        },
    }
    return _apply_scene_defaults(data)


def _fallback_parse_jst_config(text: str) -> dict[str, Any]:
    return _apply_scene_defaults({
        "site": "jst_erp",
        "name": "聚水潭 ERP 后台",
        "login_url": "https://www.erp321.com/app/order/order/list.aspx",
        "home_url": "https://www.erp321.com/app/order/order/list.aspx",
        "download_manage_url": "",
        "scenes": {
            "order_list": {
                "target_url": "https://www.erp321.com/app/order/order/list.aspx",
                "match_url_contains": [
                    "www.erp321.com/app/order/order/list.aspx",
                    "am___=LoadDataToJSON",
                ],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "reload"},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
            "product_export": {
                "target_url": "https://src.erp321.com/erp-components/goods-selector/",
                "match_url_contains": [
                    "api.erp321.com/erp/webapi/ItemApi/Export/GetExportData",
                    "owner_co_id=",
                ],
                "method": "POST",
                "auto_actions": [
                    {"type": "goto_target"},
                    {"type": "click_any_text", "texts": ["查询", "搜索"]},
                    {"type": "click_any_text", "texts": ["导出", "导出全部", "下载"]},
                ],
                "cache_minutes": 30,
                "force_refresh_before_run": True,
                "manual_login_when_failed": True,
            },
        },
    })


def load_site_config(site: str) -> dict[str, Any]:
    path = CONFIG_ROOT / f"{site}.yaml"
    if not path.exists():
        raise ConfigError(f"找不到站点配置：{path}")
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
    except ModuleNotFoundError:
        if site == "tmall_chaoshi":
            data = _fallback_parse_tmall_config(text)
        elif site == "jst_erp":
            data = _fallback_parse_jst_config(text)
        else:
            raise ConfigError("缺少 PyYAML，请先运行：pip install -r requirements.txt")
    if not data.get("site"):
        raise ConfigError(f"配置文件缺少 site：{path}")
    return _apply_scene_defaults(data)


def get_scene_config(site: str, scene: str) -> dict[str, Any]:
    config = load_site_config(site)
    scenes = config.get("scenes") or {}
    if scene not in scenes:
        raise ConfigError(f"{site} 未配置场景：{scene}")
    return scenes[scene]


def target_url_for(config: dict[str, Any], scene_config: dict[str, Any] | None = None) -> str:
    if scene_config:
        url = (scene_config.get("target_url") or "").strip()
        if url:
            return url
    for key in ("download_manage_url", "home_url", "login_url"):
        url = (config.get(key) or "").strip()
        if url:
            return url
    raise ConfigError(
        "站点 URL 还没有配置。请先编辑 config/sites/tmall_chaoshi.yaml，"
        "补充 download_manage_url 或 home_url/login_url。"
    )
