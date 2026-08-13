"""SR-MAPPO optimization loop with role-isolated actor updates."""

from __future__ import annotations

from typing import Any


class LinearDecayScheduler:
    """Progress-driven linear decay without PyTorch epoch-step ambiguity."""

    def __init__(self, optimizer: Any) -> None:
        self.optimizer = optimizer
        self.base_lrs = [float(group["lr"]) for group in optimizer.param_groups]
        self.progress = 0.0

    def step(self, progress: float) -> None:
        self.progress = min(1.0, max(0.0, float(progress)))
        for base_lr, group in zip(self.base_lrs, self.optimizer.param_groups):
            group["lr"] = base_lr * (1.0 - self.progress)

    def state_dict(self) -> dict[str, Any]:
        return {"base_lrs": list(self.base_lrs), "progress": self.progress}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.base_lrs = [float(value) for value in state["base_lrs"]]
        self.step(float(state["progress"]))


class SRMAPPOTrainer:
    def __init__(
        self,
        algorithm: Any,
        learning_rate: float = 3e-4,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        lr_decay: bool = True,
        max_grad_norm: float | None = 0.5,
    ) -> None:
        self.algorithm = algorithm
        self.value_coef = float(value_coef)
        self.entropy_coef = float(entropy_coef)
        self.lr_decay = bool(lr_decay)
        self.learning_rate = float(learning_rate)
        self.max_grad_norm = None if max_grad_norm is None else float(max_grad_norm)
        try:
            import torch
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("SR-MAPPO training requires PyTorch") from exc
        self.optimizers = {
            "uav": torch.optim.Adam(algorithm.uav_actor.parameters(), lr=learning_rate),
            "vehicle": torch.optim.Adam(algorithm.vehicle_actor.parameters(), lr=learning_rate),
            "critic": torch.optim.Adam(algorithm.critic.parameters(), lr=learning_rate),
        }
        self.schedulers = {
            role: LinearDecayScheduler(optimizer)
            for role, optimizer in self.optimizers.items()
        }
        algorithm._trainer = self

    def step_scheduler(self, progress: float) -> None:
        """Apply monotone linear learning-rate decay over normalized progress [0, 1]."""
        if self.lr_decay:
            progress = min(1.0, max(0.0, float(progress)))
            for scheduler in self.schedulers.values():
                scheduler.step(progress)

    def learning_rates(self) -> dict[str, float]:
        return {
            role: float(optimizer.param_groups[0]["lr"])
            for role, optimizer in self.optimizers.items()
        }

    def state_dict(self) -> dict[str, Any]:
        return {
            "optimizers": {role: optimizer.state_dict() for role, optimizer in self.optimizers.items()},
            "schedulers": {role: scheduler.state_dict() for role, scheduler in self.schedulers.items()},
            "lr_decay": self.lr_decay,
            "max_grad_norm": self.max_grad_norm,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.lr_decay = bool(state.get("lr_decay", self.lr_decay))
        self.max_grad_norm = state.get("max_grad_norm", self.max_grad_norm)
        for role, optimizer_state in state.get("optimizers", {}).items():
            if role in self.optimizers:
                self.optimizers[role].load_state_dict(optimizer_state)
        for role, scheduler_state in state.get("schedulers", {}).items():
            if role in self.schedulers:
                self.schedulers[role].load_state_dict(scheduler_state)

    def update(self, batch: Any, clip_epsilon: float = 0.2) -> dict[str, float]:
        import torch
        from ..common.masked_distribution import masked_categorical
        from .losses import entropy_bonus, ppo_policy_loss, value_loss
        if batch.advantages is None or batch.returns is None:
            raise ValueError("rollout must be finished before update")
        if hasattr(batch, "normalize_advantages"):
            batch.normalize_advantages()
        device = self.algorithm.device
        advantages = torch.as_tensor(batch.advantages, dtype=torch.float32, device=device)
        returns = torch.as_tensor(
            self.algorithm.normalize_returns(
                batch.returns,
                update=not bool(getattr(batch, "returns_normalized", False)),
            ),
            dtype=torch.float32,
            device=device,
        )
        batch.returns_normalized = True
        state_values = [state.get("vector", state) if isinstance(state, dict) else state for state in batch.states]
        states = torch.as_tensor(state_values, dtype=torch.float32, device=device)
        values = self.algorithm.critic(states)
        if self.algorithm.stability_components["return_normalization"]:
            old_value_data = self.algorithm.return_normalizer.normalize(batch.values, update=False)
        else:
            old_value_data = batch.values
        old_values = torch.as_tensor(old_value_data, dtype=torch.float32, device=device)
        critic_loss = value_loss(
            values,
            old_values,
            returns,
            clip_epsilon=clip_epsilon,
            clip=self.algorithm.stability_components["value_clipping"],
            huber_delta=1.0 if self.algorithm.stability_components["huber_value_loss"] else None,
        ) * self.value_coef
        self.optimizers["critic"].zero_grad()
        critic_loss.backward()
        if self.max_grad_norm is not None:
            torch.nn.utils.clip_grad_norm_(self.algorithm.critic.parameters(), self.max_grad_norm)
        self.optimizers["critic"].step()
        metrics = {"critic_loss": float(critic_loss.detach())}
        for role, actor, optimizer in (("uav", self.algorithm.uav_actor, self.optimizers["uav"]), ("vehicle", self.algorithm.vehicle_actor, self.optimizers["vehicle"])):
            policy_observations = getattr(batch, "policy_observations", {}).get(role)
            observations_source = batch.observations[role] if policy_observations is None else policy_observations
            observations = torch.as_tensor(observations_source, dtype=torch.float32, device=device)
            if observations.ndim == 3:
                time_steps, agents, features = observations.shape
                observations = observations.reshape(time_steps * agents, features)
            logits = actor(observations)
            masks = torch.as_tensor(batch.masks[role], dtype=torch.bool, device=device)
            actions = torch.as_tensor(batch.actions[role], dtype=torch.long, device=device)
            old_log_probs = torch.as_tensor(batch.log_probs[role], dtype=torch.float32, device=device)
            valid_mask = torch.as_tensor(batch.role_valid_mask(role), dtype=torch.bool, device=device)
            if masks.ndim == 3:
                masks = masks.reshape(-1, masks.shape[-1])
            actions = actions.reshape(-1)
            old_log_probs = old_log_probs.reshape(-1)
            valid_mask = valid_mask.reshape(-1)
            role_advantages = advantages
            if valid_mask.numel() != advantages.numel():
                if valid_mask.numel() % advantages.numel() != 0:
                    raise ValueError(f"actor sample count is incompatible with team advantages for role {role}")
                role_advantages = advantages.repeat_interleave(valid_mask.numel() // advantages.numel())
            valid_count = int(valid_mask.sum().item())
            metrics[f"{role}_valid_samples"] = float(valid_count)
            if valid_count == 0:
                metrics[f"{role}_policy_loss"] = 0.0
                metrics[f"{role}_entropy"] = 0.0
                continue
            distribution = masked_categorical(logits, masks)
            new_log_probs = distribution.log_prob(actions)[valid_mask]
            policy_loss = ppo_policy_loss(new_log_probs, old_log_probs[valid_mask], role_advantages[valid_mask], clip_epsilon)
            entropy = entropy_bonus(distribution.entropy()[valid_mask])
            loss = policy_loss - self.entropy_coef * entropy
            optimizer.zero_grad()
            loss.backward()
            if self.max_grad_norm is not None:
                torch.nn.utils.clip_grad_norm_(actor.parameters(), self.max_grad_norm)
            optimizer.step()
            metrics[f"{role}_policy_loss"] = float(policy_loss.detach())
            metrics[f"{role}_entropy"] = float(entropy.detach())
        return metrics

    def update_with_epochs(
        self,
        batch: Any,
        *,
        epochs: int = 1,
        clip_epsilon: float = 0.2,
        progress: float | None = None,
    ) -> dict[str, float]:
        """Run the configured number of full-batch PPO epochs."""
        if epochs < 1:
            raise ValueError("epochs must be positive")
        metrics: dict[str, float] = {}
        for epoch in range(int(epochs)):
            current = self.update(batch, clip_epsilon=clip_epsilon)
            metrics = current
            metrics["update_epoch"] = float(epoch + 1)
        if progress is not None:
            self.step_scheduler(progress)
            metrics.update({f"lr_{role}": value for role, value in self.learning_rates().items()})
        return metrics
