import os
import litellm
from typing import Optional, List, Dict, Any, cast
from content_gen.core.config_schema import EdmateConfig
from content_gen.core.config import CoreConfig
from content_gen.core.metrics import create_metrics_tracker

# Set up callbacks for observability if requested
# Users can set LITELLM_CALLBACKS=["opik"] in their .env
litellm_callbacks = os.getenv("LITELLM_CALLBACKS")
if litellm_callbacks:
    litellm.success_callback = litellm_callbacks.split(",")


class BudgetExceededError(Exception):
    """Raised when the session budget exceeds the configured limit."""
    pass


class ModelRoutingEngine:
    """
    Modular engine to route different Edmate tasks to different LLMs.
    Includes an automatic 'Economic Kill-Switch' based on configured budget.
    """

    def __init__(
        self,
        config: Optional[EdmateConfig] = None,
        *,
        api_key: Optional[str] = None,
    ):
        # Load config from YAML/JSON if not provided
        self.config = config or CoreConfig.load_from_yaml()
        self.tracker = create_metrics_tracker()
        # Per-request / BYOK key passed to litellm (never mutate os.environ).
        _k = (api_key or "").strip()
        self._api_key: Optional[str] = _k or None

    def _enforce_budget(self) -> None:
        current_cost = self.tracker.get_current_cost()
        if current_cost >= self.config.budget.max_daily_usd:
            raise BudgetExceededError(
                f"🛑 Budget Exceeded: Current session cost (${current_cost:.4f}) "
                f"has reached the limit (${self.config.budget.max_daily_usd:.2f})."
            )

    def _select_model(self, task_type: str) -> str:
        if task_type == "extraction":
            return self.config.model_routing.extraction or "gemini/gemini-1.5-pro"
        if task_type == "validation":
            return self.config.model_routing.validation or "openai/gpt-4o"
        return self.config.model_routing.generation or "anthropic/claude-3-haiku"

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str],
        images: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if images:
            content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    def _completion_kwargs(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        task_type: str,
        json_mode: bool,
        api_key: Optional[str],
    ) -> Dict[str, Any]:
        _key = (api_key or "").strip() or self._api_key
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "timeout": 120 if task_type == "extraction" else 180,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if _key:
            kwargs["api_key"] = _key
        return kwargs

    def _extract_message_text(self, response: Any) -> str:
        response_obj = cast(Any, response)
        if not hasattr(response_obj, "choices"):
            raise RuntimeError("Unexpected streaming response received from litellm.completion")
        content = response_obj.choices[0].message.content
        return content if isinstance(content, str) else str(content)

    def generate_content(
        self,
        prompt: str,
        task_type: str = "generation",
        system_prompt: Optional[str] = None,
        images: Optional[List[str]] = None,
        json_mode: bool = False,
        api_key: Optional[str] = None,
    ) -> str:
        """
        Routes the task to the appropriate model based on task_type.
        Checks budget before execution (Economic Kill-Switch).
        """
        self._enforce_budget()
        model = self._select_model(task_type)
        messages = self._build_messages(prompt, system_prompt, images)
        kwargs = self._completion_kwargs(model, messages, task_type, json_mode, api_key)
        response = litellm.completion(**kwargs)
        self.tracker.log_usage(response)
        return self._extract_message_text(response)

    def get_summary(self) -> Dict[str, Any]:
        """Returns the current metrics and routing config."""
        return {
            "metrics": self.tracker.metrics,
            "config": self.config.dict()
        }
