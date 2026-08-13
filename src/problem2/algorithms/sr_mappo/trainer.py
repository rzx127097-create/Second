"""SR-MAPPO optimization loop with role-isolated actor updates."""

from __future__ import annotations

from typing import Any


class SRMAPPOTrainer:
    def __init__(self, algorithm: Any, learning_rate: float = 3e-4, value_coef: float = 0.5, entropy_coef: float = 0.01, lr_decay: bool = True) -> None:
        self.algorithm = algorithm
        self.value_coef = float(value_coef)
        self.entropy_coef = float(entropy_coef)
        self.lr_decay = bool(lr_decay)
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
            role: torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda progress: max(0.0, 1.0 - float(progress)))
            for role, optimizer in self.optimizers.items()
        }
        algorithm._trainer = self

    def step_scheduler(self, progress: float) -> None:
        """Apply monotone linear learning-rate decay over normalized progress [0, 1]."""
        if self.lr_decay:
            for scheduler in self.schedulers.values():
                scheduler.step(float(progress))

    def state_dict(self) -> dict[str, Any]:
        return {
            "optimizers": {role: optimizer.state_dict() for role, optimizer in self.optimizers.items()},
            "schedulers": {role: scheduler.state_dict() for role, scheduler in self.schedulers.items()},
            "lr_decay": self.lr_decay,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
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
        advantages = torch.as_tensor(batch.advantages, dtype=torch.float32)
        returns = torch.as_tensor(self.algorithm.normalize_returns(batch.returns, update=True), dtype=torch.float32)
        states = torch.as_tensor(batch.states, dtype=torch.float32)
        values = self.algorithm.critic(states)
        critic_loss = value_loss(values, values.detach(), returns, clip_epsilon=clip_epsilon) * self.value_coef
        self.optimizers["critic"].zero_grad()
        critic_loss.backward()
        self.optimizers["critic"].step()
        metrics = {"critic_loss": float(critic_loss.detach())}
        for role, actor, optimizer in (("uav", self.algorithm.uav_actor, self.optimizers["uav"]), ("vehicle", self.algorithm.vehicle_actor, self.optimizers["vehicle"])):
            observations = torch.as_tensor(batch.observations[role], dtype=torch.float32)
            logits = actor(observations)
            masks = torch.as_tensor(batch.masks[role], dtype=torch.bool)
            actions = torch.as_tensor(batch.actions[role], dtype=torch.long)
            old_log_probs = torch.as_tensor(batch.log_probs[role], dtype=torch.float32)
            distribution = masked_categorical(logits, masks)
            policy_loss = ppo_policy_loss(distribution.log_prob(actions), old_log_probs, advantages, clip_epsilon)
            loss = policy_loss - self.entropy_coef * entropy_bonus(distribution.entropy())
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            metrics[f"{role}_policy_loss"] = float(policy_loss.detach())
        return metrics
