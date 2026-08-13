# Second
# Problem 2 SR-MAPPO Code Framework

This repository contains the implementation framework for the thesis Chapter 4
road-constrained air-ground cooperative pesticide replenishment problem. The
flagship algorithm is **SR-MAPPO** with separate UAV and vehicle actors and a
centralized team critic. The vehicle replenishes pesticide only; it does not
charge or exchange batteries.

## Current maturity

The repository is at M2: deterministic domain, environment, road, baseline,
artifact, and SR-MAPPO interfaces are covered by automated tests. Configuration
values in `configs/` are marked `provisional`; no formal result or superiority
claim is supported until engineering sources, resource activation audits, pilot
runs, and sealed-test statistics are completed.

## Layout

- `configs/`: parameter registry, six scales, SR-MAPPO flags, and formal matrix.
- `src/problem2/domain/`: bounded pesticide resources and request lifecycle.
- `src/problem2/field/`, `environment/`: field dynamics and frozen event order.
- `src/problem2/road/`, `demand/`: metric road graph, shortest paths, rendezvous.
- `src/problem2/environment/`: role observations, masks, critic state, rewards.
- `src/problem2/algorithms/`: SR-MAPPO actors, critic, GAE, PPO losses, checkpoints.
- `src/problem2/baselines/`: diagnostic and resource-matched planning baselines.
- `src/problem2/experiments/`: immutable jobs, retries, shared evaluation.
- `src/problem2/artifacts/`: log validation, summaries, figures, tables, manifests.

## Verification

```powershell
pytest -q
```

The current CPU environment verifies NumPy/domain/environment/experiment paths.
Install the optional reinforcement-learning dependency before neural-network
tests or GPU training:

```powershell
pip install -e ".[rl]"
```

Training and matrix entry points intentionally stop while the parameter registry
is provisional. Formal jobs must record configuration hash, Git commit, method,
scale, seed, scenario and raw event-complete logs before artifact generation.
