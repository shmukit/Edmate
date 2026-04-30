import os
import litellm
from typing import Optional, List, Dict, Any, cast
from content_gen.core.config_schema import EdmateConfig
from content_gen.core.config import CoreConfig
from content_gen.core.metrics import MetricsTracker

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

    def __init__(self, config: Optional[EdmateConfig] = None):
        # Load config from YAML/JSON if not provided
        self.config = config or CoreConfig.load_from_yaml()
        self.tracker = MetricsTracker()

    def generate_content(
        self,
        prompt: str,
        task_type: str = "generation",
        system_prompt: Optional[str] = None,
        images: Optional[List[str]] = None,
        json_mode: bool = False
    ) -> str:
        """
        Routes the task to the appropriate model based on task_type.
        Checks budget before execution (Economic Kill-Switch).
        """
        # 1. Check Budget (The Safety Layer)
        current_cost = self.tracker.get_current_cost()
        if current_cost >= self.config.budget.max_daily_usd:
            raise BudgetExceededError(
                f"🛑 Budget Exceeded: Current session cost (${current_cost:.4f}) "
                f"has reached the limit (${self.config.budget.max_daily_usd:.2f})."
            )

        # 2. Determine model
        if task_type == "extraction":
            model = self.config.model_routing.extraction or "gemini/gemini-1.5-pro"
        elif task_type == "validation":
            model = self.config.model_routing.validation or "openai/gpt-4o"
        else:
            model = self.config.model_routing.generation or "anthropic/claude-3-haiku"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Handle Multimodal
        if images:
            content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
            for img in images:
                content.append(
                    {"type": "image_url", "image_url": {"url": img}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})

        # 3. Execute call
        response = litellm.completion(
            model=model,
            messages=messages,
            response_format={"type": "json_object"} if json_mode else None,
            timeout=120 if task_type == "extraction" else 180
        )

        # 4. Log usage (The Analytics Layer)
        self.tracker.log_usage(response)

        response_obj = cast(Any, response)
        if not hasattr(response_obj, "choices"):
            raise RuntimeError("Unexpected streaming response received from litellm.completion")

        content = response_obj.choices[0].message.content
        return content if isinstance(content, str) else str(content)

    def get_summary(self) -> Dict[str, Any]:
        """Returns the current metrics and routing config."""
        return {
            "metrics": self.tracker.metrics,
            "config": self.config.dict()
        }
