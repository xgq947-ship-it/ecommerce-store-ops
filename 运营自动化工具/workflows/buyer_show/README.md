# buyer_show workflow

把「买家秀自动分组、压缩、登记表回写」从单脚本升级为 step 化流程。这是既有任务的**包装层**，不替代旧命令。

## 入口

旧命令（不变，走 `tasks/buyer_show.py`）：

```bash
python3 run.py buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838" --dry-run
python3 run.py buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838" --reset-rotation
```

新 workflow 入口：

```bash
python3 run.py workflow buyer_show --dry-run
python3 run.py workflow buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838" --dry-run
python3 run.py workflow buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838"   # 真实打包+回写
```

支持参数（透传给复用逻辑）：`--buyer-show-path`、`--model`、`--workbook`、`--groups`、`--batch`、`--images-per-group`、`--allow-total-shortage`、`--desktop`、`--reset-rotation`、`--rotation-key`、`--dry-run`。

> `--buyer-show-path` 与 `--model` 为真实执行必填；无这两个参数时 dry-run 会安全跳过（仅作占位预览）。

## 步骤

| step | 作用 | dry-run 行为 |
|------|------|--------------|
| `check_inputs` | 解析参数、定位登记表、计算轮询 key | 缺参数/路径时安全跳过 |
| `scan_buyer_show_sources` | 匹配型号订单、按日期分批（`read_matches`） | 只读 |
| `select_groups` | 规划分组与轮询游标（`select_group_batches`） | 只读；分组不足时记 `can_execute=False` |
| `build_zip_packages` | 打包买家秀 zip（`package_zip`/`verify_zip`） | **跳过，不打包、不复制图片** |
| `update_register` | 备份 + 回写登记表 + 推进轮询游标 | **跳过，登记表与轮询状态零改写** |
| `collect_artifacts` | 汇总 zip、备份、轮询信息 | 只汇总 |

## dry-run 安全策略

1. **不打包、不动图片**：`build_zip_packages` 在 dry-run 跳过（旧任务也只复制图片入 zip、从不移动原图）。
2. **登记表零改写**：`update_register` 在 dry-run 跳过，不 `backup_workbook`、不 `patch_workbook`（不触碰图片/DISPIMG/cellimages 结构）。
3. **轮询状态零改写**：dry-run 不重置（`reset_rotation_cursor`）、不推进（`set_rotation_cursor`）轮询游标。
4. 分组不足、图片不足等保护逻辑沿用 legacy（`verify_group_image_counts` 要求每组多于 3 张），dry-run 下以 `can_execute=False` + 原因呈现。

## 真实执行需要的参数

- 必填：`--buyer-show-path`、`--model`。
- 真实回写登记表：去掉 `--dry-run`。

## 边界

- 不涉及平台调用（纯本地图片 + Excel 操作）。
- 复用 legacy 的 `read_matches / select_group_batches / package_zip / verify_zip / patch_workbook / set_rotation_cursor / grouped_sources`，不重写算法或 Excel ZIP/XML 补丁逻辑。
