# Problem 2 SR-MAPPO Code Framework

本仓库是论文第 4 章问题 2 的可运行代码框架：道路约束下的空地异构协同施药，地面车辆只负责药液补给，不充电、不交换电池。当前交付门为 M2。配置和 formal matrix 仍为 `provisional`，因此 smoke 运行仅用于工程链路验证，不能写成论文正式结果或优越性结论。

## 环境与安装

Windows PowerShell、Python 3.11（`python --version` 应为 3.11.x）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .
# 需要 SR-MAPPO 神经网络训练时：
pip install -e ".[rl]"
```

## 验证

```powershell
pytest -q
python -m compileall -q src scripts
git diff --check
```

完整的端到端 smoke、恢复、validation 评估和 artifact 链路见 [`docs/verification/complete-project-runbook.md`](docs/verification/complete-project-runbook.md)。

## 唯一允许的执行入口

参数仍是 provisional 时，只有带显式 `--smoke` 的最小执行被允许。训练、评估和矩阵命令的 smoke 输出必须保留 `provisional` 标记。未带 `--smoke` 的 formal 训练/评估会拒绝；`sealed_test` 还要求 verified 参数、冻结策略和 deterministic 执行。

```powershell
python scripts/train.py --config-dir configs --scale s1 --seed 0 --updates 1 --output-root runs --smoke
python scripts/evaluate.py --config-dir configs --checkpoint <runs\checkpoints\job-id.pt> --split validation --scenario val_001 --smoke
python scripts/run_matrix.py --config-dir configs --output-root runs --smoke --max-jobs 1
python scripts/build_artifacts.py <runs\raw\evaluation-*.jsonl> --output runs\artifacts --manifest runs\artifacts\manifest.json
```

正式结果仍需 M3 的工程参数证据、独立 validation 多 seed；M4 需冻结完整矩阵、sealed test 和可复核 manifest。道路输入是仿真约束，不代表真实道路或真实部署；当前代码证据边界是 M2 的场景、事件、资源守恒和 SR-MAPPO 接口。

## Canonical methods

正式矩阵只允许以下五个 key：`sr_mappo_mobile`、`sr_mappo_fixed`、`sr_mappo_astar`、`mappo_mobile`、`sr_mappo_two_stage`。`HAPPO` 和 `AG-SR-MAPPO` 不属于本项目协议，禁止写入矩阵、日志或论文结论。
