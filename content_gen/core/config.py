import yaml
from pathlib import Path
from typing import Optional
from content_gen.core.schemas import ModelConfig


class CoreConfig:
    """
    Handles loading and validating the Edmate configuration from YAML.
    """

    @staticmethod
    def load_from_yaml(config_path: Optional[str] = None) -> ModelConfig:
        """
        Loads a YAML file and parses it into a ModelConfig object.
        If config_path is not provided, looks for 'edmate_config.yaml' in the project root.
        """
        if config_path is None:
            # Look for config in the project root relative to this file
            root_path = Path(__file__).parent.parent.parent
            path = root_path / "edmate_config.yaml"
        else:
            path = Path(config_path)

        if not path.exists():
            print(f"ℹ️ Config file {path} not found. Using defaults.")
            return ModelConfig()

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)

            if not data:
                return ModelConfig()

            # Extract routing and budget info
            routing = data.get("model_routing", {})
            budget = data.get("budget", {})
            img_settings = data.get("storage_settings", {})
            ext_settings = data.get("extraction_settings", {})

            return ModelConfig(
                extraction_model=routing.get("extraction") or "gemini/gemini-1.5-pro",
                generation_model=routing.get("generation") or "anthropic/claude-3-haiku",
                validation_model=routing.get("validation") or "openai/gpt-4o",
                max_budget=budget.get("max_daily_usd", 10.0),
                image_mode=img_settings.get("image_mode") or "cdn",
                extraction_engine=ext_settings.get("engine") or "pdf_extract_kit",
                min_question_number=ext_settings.get("min_question_number", 1),
                max_question_number=ext_settings.get("max_question_number", 40),
                question_detection_mode=ext_settings.get("question_detection_mode") or "balanced"
            )
        except Exception as e:
            print(f"⚠️ Error loading config: {e}. Using defaults.")
            return ModelConfig()

    @staticmethod
    def save_defaults(config_path: str = "edmate_config.yaml.example"):
        """Saves a template configuration file."""
        defaults = {
            "model_routing": {
                "extraction": "gemini/gemini-1.5-pro",
                "generation": "anthropic/claude-3-haiku",
                "validation": "openai/gpt-4o"
            },
            "budget": {
                "max_daily_usd": 10.0
            },
            "storage_settings": {
                "image_mode": "cdn"
            },
            "extraction_settings": {
                "engine": "pdf_extract_kit",
                "min_question_number": 1,
                "max_question_number": 40,
                "question_detection_mode": "balanced"
            },
            "observability": {
                "litellm_callbacks": ["opik"]
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(defaults, f, default_flow_style=False)
        print(f"✅ Template config saved to {config_path}")
