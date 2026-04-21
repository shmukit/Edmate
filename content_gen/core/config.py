import yaml
from pathlib import Path
from typing import Optional
from .schemas import ModelConfig

class CoreConfig:
    """
    Handles loading and validating the Edmate configuration from YAML.
    """
    
    @staticmethod
    def load_from_yaml(config_path: str = "edmate_config.yaml") -> ModelConfig:
        """
        Loads a YAML file and parses it into a ModelConfig object.
        If the file doesn't exist, returns default configuration.
        """
        path = Path(config_path)
        
        if not path.exists():
            print(f"ℹ️ Config file {config_path} not found. Using defaults.")
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
                extraction_engine=ext_settings.get("engine") or "pdf_extract_kit"
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
            "observability": {
                "litellm_callbacks": ["opik"]
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(defaults, f, default_flow_style=False)
        print(f"✅ Template config saved to {config_path}")
