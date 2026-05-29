# company_nas_listing workflow

把「公司网盘下载产品」从单脚本升级为 step 化流程。这是既有任务的**包装层**，不替代旧命令。

## 入口

旧命令（不变，走 `tasks/company_nas_listing.py`）：

```bash
python3 run.py "从公司网盘下载奥克斯足疗机AQA-JT-RFY06" --dry-run
python3 run.py company_nas_listing --brand 奥克斯 --category 足疗机 --models AQA-JT-RFY06 --dry-run
```

新 workflow 入口：

```bash
python3 run.py workflow company_nas_listing --dry-run
python3 run.py workflow company_nas_listing --brand 奥克斯 --category 足疗机 --models AQA-JT-RFY06 --dry-run
python3 run.py workflow company_nas_listing --text "从公司网盘下载奥克斯足疗机AQA-JT-RFY06"   # 真实下载
```

支持参数（透传给复用逻辑）：`--text`（自然语言）、`--brand`、`--category`、`--models`、`--models-file`、`--target-root`、`--jst-workbook`、`--include-buyer-show`、`--keep-mounted`、`--no-replace`、`--skip-excel`、`--dry-run`。

> 真实执行必须提供品牌 + 类目 + 型号（可经 `--text` 自然语言或显式参数）。无这些时 dry-run 安全跳过并提示。

## 步骤

| step | 作用 | dry-run 行为 |
|------|------|--------------|
| `check_inputs` | 解析参数（含自然语言）、校验品牌/类目/型号 | 缺参数时安全跳过 |
| `parse_listing_request` | 解析型号规格（`load_models`） | 只解析 |
| `search_nas_index` | 挂载 NAS + 索引定位源目录 + 选材计数 | 只读预览 |
| `copy_product_assets` | 复制素材到目标目录（`copy_product`） | **跳过：不复制/移动任何文件** |
| `build_listing_data` | 匹配聚水潭 + 生成上架数据 Excel | **跳过：不生成/覆盖 Excel** |
| `collect_artifacts` | 校验产出、收尾卸载 NAS | 卸载 + 汇总 |

## dry-run 安全策略

1. **不复制/移动文件**：`copy_product_assets` 在 dry-run 跳过（且 legacy `copy_product` 本身 dry-run 也为 no-op）。
2. **不删除 NAS 文件**：选材为只读遍历，目标目录在 dry-run 不被清理或写入。
3. **不覆盖已有上架资料**：`build_listing_data` 在 dry-run 跳过，不写 `上架数据.xlsx`。
4. **保留自然语言兼容**：`--text` 经 legacy `parse_natural_text` 解析品牌/类目/型号。
5. 收尾卸载与 legacy 一致；NAS 不可达 / 源目录缺失时 dry-run 安全降级。

## 边界

- 不涉及电商平台调用；NAS 挂载/卸载、素材选取规则复用 legacy。
- 复用 `tasks/company_nas_listing.py` 的 `resolve_args / load_models / indexed_model_source / selected_files / copy_product / match_jst / save_listing / validate_outputs`，不重写算法。
