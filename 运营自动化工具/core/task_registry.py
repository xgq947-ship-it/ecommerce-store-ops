from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TASKS = {
    "buyer_show": {
        "aliases": ["buyer_show", "买家秀自动化", "买家秀打包", "生成买家秀评价", "评价图分组压缩"],
        "module": "tasks.buyer_show",
        "script": ROOT / "tasks" / "buyer_show.py",
        "description": "买家秀自动分组、压缩和登记表回写",
    },
    "append_brush_orders": {
        "aliases": ["append_brush_orders", "刷单表格登记", "追加刷单登记", "登记刷单表格", "获取刷单数据源", "微信刷单表格登记"],
        "module": "tasks.append_brush_orders",
        "script": ROOT / "tasks" / "append_brush_orders.py",
        "description": "刷单表格登记",
    },
    "tag_jst_brush_orders": {
        "aliases": ["tag_jst_brush_orders", "聚水潭刷单订单打标", "刷单订单插黄旗", "刷单订单备注sfeizao", "特殊件标记"],
        "module": "tasks.jst_order_label.main",
        "script": ROOT / "tasks" / "jst_order_label" / "main.py",
        "description": "聚水潭刷单订单打标",
    },
    "jst_brush_reimburse_workorder": {
        "aliases": ["jst_brush_reimburse_workorder", "聚水潭刷单报销工单", "刷单报销登记", "运营特殊单报销打款"],
        "module": "tasks.jst_brush_reimburse_workorder",
        "script": ROOT / "tasks" / "jst_brush_reimburse_workorder.py",
        "description": "聚水潭刷单报销工单",
    },
    "company_nas_listing": {
        "aliases": ["company_nas_listing", "公司网盘下载产品", "NAS产品资料下载", "下载产品资料并生成上架数据"],
        "module": "tasks.company_nas_listing",
        "script": ROOT / "tasks" / "company_nas_listing.py",
        "description": "公司网盘产品资料下载和上架数据生成",
    },
    "company_nas_index": {
        "aliases": ["company_nas_index", "扫描公司网盘目录", "更新公司网盘索引", "建立NAS目录索引", "公司网盘目录层级记录", "搜索公司网盘文件"],
        "module": "tasks.company_nas_index",
        "script": ROOT / "tasks" / "company_nas_index.py",
        "description": "公司网盘产品资料目录索引和搜索",
    },
    "process_maochao_bills": {
        "aliases": ["process_maochao_bills", "运行猫超账单整理", "整理猫超账单", "猫超账单整理", "处理猫超月账单数据", "整理猫超月账单数据"],
        "module": "tasks.tmall_monthly_bill.main",
        "script": ROOT / "tasks" / "tmall_monthly_bill" / "main.py",
        "description": "猫超月账单整理",
    },
    "update_jst_products": {
        "aliases": ["update_jst_products", "更新聚水潭商品资料"],
        "module": "tasks.jst_product_sync.main",
        "script": ROOT / "tasks" / "jst_product_sync" / "main.py",
        "description": "更新聚水潭商品资料",
    },
    "update_maochao_goods": {
        "aliases": ["update_maochao_goods", "更新猫超商品列表"],
        "module": "tasks.tmall_product_list.main",
        "script": ROOT / "tasks" / "tmall_product_list" / "main.py",
        "description": "更新猫超商品列表",
    },
    "tmcs_sync_jst_shop_goods": {
        "aliases": [
            "tmcs_sync_jst_shop_goods",
            "聚水潭商品信息同步猫超",
            "猫超商品信息同步聚水潭",
            "平台商品ID同步聚水潭",
            "猫超商品同步聚水潭",
        ],
        "module": "tasks.tmcs_sync_jst_shop_goods.main",
        "script": ROOT / "tasks" / "tmcs_sync_jst_shop_goods" / "main.py",
        "description": "猫超平台商品信息同步聚水潭店铺商品资料",
    },
    "jst_pickup_watch": {
        "aliases": ["jst_pickup_watch", "聚水潭揽收监控", "聚水潭订单揽收监控", "订单揽收异常提醒"],
        "module": "tasks.jst_pickup_watch",
        "script": ROOT / "tasks" / "jst_pickup_watch.py",
        "description": "聚水潭付款订单揽收时效风险监控",
    },
    "retry_queue": {
        "aliases": ["retry_queue", "查看失败任务", "查看重试队列", "重试失败任务", "重放失败任务"],
        "module": "tasks.retry_queue",
        "script": ROOT / "tasks" / "retry_queue.py",
        "description": "查看或重放失败任务队列",
    },
}

TASK_ALIASES = {
    alias: task_name
    for task_name, config in TASKS.items()
    for alias in config["aliases"]
}

FUZZY_TASK_RULES = [
    ("buyer_show", (("买家秀",), ("评价", "生成"), ("评价", "压缩"))),
    ("append_brush_orders", (("刷单", "登记"), ("刷单", "表格"), ("刷单", "追加"), ("刷单", "数据源"), ("微信", "刷单"))),
    ("tag_jst_brush_orders", (("聚水潭", "刷单", "打标"), ("刷单", "黄旗"), ("刷单", "备注", "sfeizao"), ("特殊件", "标记"))),
    ("jst_brush_reimburse_workorder", (("聚水潭", "刷单", "报销", "工单"), ("刷单", "报销", "登记"), ("特殊单", "报销", "打款"))),
    ("process_maochao_bills", (("猫超", "账单"), ("猫超", "对账"), ("月账单",), ("HDB",))),
    ("update_maochao_goods", (("猫超", "商品列表"), ("猫超", "商品", "更新"))),
    ("tmcs_sync_jst_shop_goods", (("聚水潭", "商品信息", "同步", "猫超"), ("猫超", "商品", "同步", "聚水潭"), ("平台商品ID", "同步", "聚水潭"))),
    ("update_jst_products", (("聚水潭", "商品资料"), ("聚水潭", "资料"), ("JST", "商品"))),
    ("jst_pickup_watch", (("聚水潭", "揽收", "监控"), ("订单", "揽收", "异常"), ("揽收", "提醒"))),
    ("company_nas_index", (("公司网盘", "索引"), ("NAS", "索引"), ("公司网盘", "目录", "扫描"), ("公司网盘", "文件", "搜索"), ("搜索", "公司网盘", "文件"))),
    ("company_nas_listing", (("公司网盘",), ("NAS", "产品"), ("网盘", "下载"), ("产品资料", "上架"))),
    ("retry_queue", (("查看", "失败", "任务"), ("查看", "重试", "队列"), ("重试", "失败", "任务"), ("重放", "失败", "任务"))),
]


def normalize_task_text(text: str) -> str:
    return text.replace("剧水潭", "聚水潭")


def task_scripts() -> dict[str, Path]:
    return {name: config["script"] for name, config in TASKS.items()}


def resolve_task(task: str) -> str:
    task = normalize_task_text(task)
    if task in TASKS:
        return task
    if task in TASK_ALIASES:
        return TASK_ALIASES[task]

    normalized = task.replace(" ", "").replace("_", "").lower()
    for task_name, patterns in FUZZY_TASK_RULES:
        for keywords in patterns:
            if all(keyword.lower() in normalized for keyword in keywords):
                return task_name

    valid_names = "、".join(sorted([*TASKS, *TASK_ALIASES]))
    raise SystemExit(f"未知任务：{task}\n可用任务：{valid_names}\n也支持类似说法，例如：刷单登记、猫超刷单表格登记、店铺刷单登记、整理猫超对账、更新聚水潭资料。")
