# workflow runtime

把业务任务从「脚本执行」升级为「步骤化流程执行」。

旧任务（`tasks/`）是单脚本黑盒：`run.py` 解析任务名 → 跑整个 `main.py` → 落 stdout/日志/`runtime/context`，无法记录中间步骤、产物、失败点。workflow runtime 在**不破坏旧命令**的前提下，把同一条业务流水线拆成有状态的步骤，逐步落盘运行记录。

## 旧 tasks 与新 workflows 的关系

- 两者并存，旧命令完全不变：
  ```bash
  python3 run.py --list
  python3 run.py 猫超账单整理
  python3 run.py 猫超账单整理 --dry-run
  ```
- 新增 workflow 入口（不影响任何旧任务）：
  ```bash
  python3 run.py workflow <workflow_id> [--dry-run] [--month YYYY-MM]
  python3 run.py workflow demo --dry-run
  python3 run.py workflow tmall_monthly_bill --dry-run
  python3 run.py workflow tmcs_sku_roi --sku-code AUXAMUZ8102R01 --dry-run
  python3 run.py workflow tmcs_xp_workorder_watch --dry-run
  ```
- workflow 是**包装层**：复用 `tasks/` 下成熟的业务实现（解析、Excel、下载），只把它们重新编排成步骤。不替代、不重写旧任务。

调用关系：

```text
run.py
  ├─ <中文任务名> → core/task_registry.py → tasks/*/main.py            （旧链路，不变）
  └─ workflow <id> → core/runtime/registry.py → workflows/<id>/workflow.py
                       → core/runtime WorkflowRunner → 复用 tasks/* 成熟函数
```

## 目录与组成

```text
core/runtime/            # runtime 内核（不含业务）
  models.py              # Artifact / WorkflowStep / Workflow / StepRun / TaskRun
  result.py              # OpsResult / success_result() / failure_result()
  storage.py             # RunStorage：落 runtime/runs/YYYY-MM/run_xxx/
  workflow.py            # build_workflow() / step() 构造校验
  runner.py              # WorkflowRunner / StepContext
  registry.py            # discover_workflow()：扫描 workflows/<id>/workflow.py

workflows/               # 业务 workflow（编排层，不含平台逻辑）
  <id>/
    workflow.py          # 导出 build_workflow() -> Workflow
    steps.py             # step handler，复用 tasks/* 成熟函数
    README.md
```

运行记录落盘布局：

```text
runtime/runs/YYYY-MM/run_xxx/
  run.json               # 整体 run + 全部 step 快照 + 汇总 outputs/artifacts
  steps/<step_id>.json   # 每个 step 的独立记录
  artifacts.json         # 全部 Artifact 汇总
```

`run.py workflow` 还会额外写一条 `logs/workflow_<id>_<stamp>.json` 和外层 `runtime/context`，与旧任务保持一致的可观测性。

## 运行归档与产物检索

每次 workflow 运行结束，`WorkflowRunner` 会把一条精简记录追加到全局索引 `runtime/runs/index.jsonl`（run_id、workflow、状态、时间、run_dir、产物摘要），便于跨 run 检索而无需逐个打开 `run.json`。

```bash
# 列出最近运行（默认 20 条，可按 workflow 过滤）
python3 run.py runs --limit 10
python3 run.py runs --workflow tmall_monthly_bill

# 从现有 run.json 重建索引（回填历史运行）
python3 run.py runs --reindex

# 检索产物（按关键词 / role / platform / month）
python3 run.py artifacts 月账单
python3 run.py artifacts --role output --platform tmcs
python3 run.py artifacts --month 2026-05
```

索引由 `core.runtime.RunIndex` 维护，落在 `runtime/runs/` 内（已被 `.gitignore` 排除，不进版本库）。索引写入失败不会影响 workflow 主流程。

## 新增一个 workflow 的标准方式

1. 在 `workflows/` 下新建目录 `workflows/<id>/`，加空 `__init__.py`。
2. 写 `steps.py`：每个 step 是一个 `handler(ctx) -> OpsResult` 函数，**复用** `tasks/` 下现成业务函数，不在这里重写业务逻辑。
3. 写 `workflow.py`：导出 `build_workflow() -> Workflow`，用 `step(...)` 声明步骤顺序。
4. 验证：
   ```bash
   python3 run.py workflow <id> --dry-run
   ```
5. 写 `README.md` 说明步骤、dry-run 行为、产物、边界。

无需改动 `run.py` 或 `registry.py`——`workflow` 子命令自动按目录发现。

当前已落地的 workflow：

- `append_brush_orders`
- `buyer_show`
- `company_nas_index`
- `company_nas_listing`
- `demo`
- `jst_brush_reimburse_workorder`
- `jst_order_invoice_workorder`
- `jst_order_label`
- `jst_pickup_watch`
- `jst_product_sync`
- `retry_queue`
- `tmall_monthly_bill`
- `tmall_product_list`
- `tmcs_sku_roi`
- `tmcs_sync_jst_shop_goods`
- `tmcs_xp_workorder_watch`

## step 怎么写

```python
from core.runtime import StepContext, success_result, failure_result, Artifact

def my_step(ctx: StepContext):
    # ctx.inputs：workflow 输入（含 dry_run、args、month 等）
    # ctx.dry_run：是否预览；dry-run 下严禁触发真实下载/写文件
    # ctx.state：跨 step 传递 Python 对象的暂存区（不落 JSON）
    if ctx.dry_run:
        return success_result(outputs={"skipped": True, "reason": "dry-run 跳过"})

    value = do_real_work(ctx.state["source"])      # 复用既有业务函数
    ctx.state["value"] = value                      # 传给后续 step
    return success_result(outputs={"value_count": len(value)})
```

`step()` 参数：

- `id`：步骤唯一标识，决定 `steps/<id>.json` 文件名。
- `name`：人读名称。
- `handler`：上面的函数。
- `required`（默认 `True`）：失败则**中断**整个 workflow，TaskRun 记 `failed`。
- `required=False`：失败只记 `failed` 但**继续**后续步骤。
- `retryable`（默认 `False`）：当前只透传记录，runtime 不做自动重试。

handler 返回约定：

- 成功：`success_result(outputs=..., artifacts=...)`（dry-run 下 step 状态记 `dry_run_success`）。
- 失败：`failure_result(errors=..., outputs=...)`，或直接抛异常（runner 自动转成 failed，含异常类型与消息）。
- handler 必须返回 `OpsResult`；返回别的类型会被判为失败。

## Artifact 怎么记录

产物用 `core.runtime.Artifact`，字段：`type / role / name / path / platform / month / metadata`。

两种记录方式（可混用）：

```python
art = Artifact(type="xlsx", role="output", name=p.name, path=str(p), platform="tmcs", month="5")
return success_result(artifacts=[art])     # 方式一：随结果返回
# 方式二：ctx.add_artifact(art)            # 在 handler 内随时收集
```

runner 会把每个 step 的 artifacts 汇总到 `TaskRun.artifacts`，结束时写 `artifacts.json`。约定 `role` 表达用途（如 `hdb_source / statement_list / promotion_source / output`），便于下游消费。

## 统一通知

`core.runtime.send_notification` 是各 workflow 共用的通知入口（提醒 / 失败告警），把「dry-run 只产预览、不发送；真实执行才推送」这条安全语义收敛到一处：

```python
from core.runtime import send_notification

# dry-run：绝不真实发送，只返回 {"sent": False, "dry_run": True, "preview": content}
notification = send_notification(content, dry_run=ctx.dry_run, msgtype="markdown")
```

- 底层复用本机 `~/.hermes/scripts/send_wecom.py`（本地通知工具，不是电商平台 API）。
- 可注入 `sender=` 便于测试，不传则懒加载真实 `send_wecom`。
- `jst_pickup_watch` 的 `notify_if_needed` 已改为复用此入口；新 workflow 要发提醒时统一走它，不要各自直接 import `send_wecom`。

## 哪些代码不能写进业务层（workflows/ 与 tasks/）

与既有边界一致：

- 平台 URL、Cookie / Token / LocalStorage。
- Playwright / CDP / 浏览器页面操作、Selector、上传下载。
- `requests` / `httpx` 直接请求平台、scene 学习与请求重放。
- `import sessionhub.*`。

平台动作一律通过 `clients/ops_cli_client.py` 调 `ops --json ...`（沉在 `Ops-Cli`）。workflow 的 step 只负责编排与运行记录，dry-run 不得触发真实平台下载或写最终文件。

## 如何验证旧任务没有被破坏

```bash
# 1. 旧任务列表与触发不变
python3 run.py --list

# 2. 旧命令照常工作（dry-run）
python3 run.py 更新猫超商品列表 --dry-run
python3 run.py 更新聚水潭资料 --dry-run
python3 run.py 猫超账单整理 --dry-run

# 3. 回归测试（含旧任务注册与 run.py 调度）
python3 -m pytest tests/test_task_registry.py tests/test_run.py -q

# 4. workflow runtime 自身与全量
python3 -m pytest tests/test_workflow_runtime.py -q
python3 -m pytest -q
```

workflow 子命令在 `run.py` 的 `main()` 最早处拦截 `sys.argv[1] == "workflow"`，**完全绕开** `resolve_task`，因此不影响任何中文任务名、别名或模糊触发。
