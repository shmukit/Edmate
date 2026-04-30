from typing import Optional, Union
from pathlib import Path
from content_gen.core.config_loader import ConfigLoader
from content_gen.core.config_schema import EdmateConfig


class CoreConfig:
    """
    Legacy wrapper for Edmate configuration.
    Now uses ConfigLoader internally to support both YAML and JSON.
    """

    @staticmethod
    def load_from_yaml(config_path: Optional[Union[str, Path]] = None) -> EdmateConfig:
        """
        Loads configuration using ConfigLoader.
        Maintains the old method name for backward compatibility.
        """
        return ConfigLoader.load_config(config_path)

    @staticmethod
    def save_defaults(config_path: str = "edmate_config.json.example"):
        """Saves a template configuration file."""
        ConfigLoader.save_template(config_path, format="json" if config_path.endswith(".json") else "yaml")

