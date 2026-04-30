import yaml
import json
from pathlib import Path
from typing import Optional, Union, Any
from pydantic import ValidationError
from content_gen.core.config_schema import EdmateConfig

class ConfigLoader:
    """
    Unified loader for Edmate configuration (YAML/JSON).
    Supports backward compatibility and schema validation via Pydantic.
    """
    
    DEFAULT_CONFIG_NAME = "edmate_config"
    SUPPORTED_EXTENSIONS = [".yaml", ".yml", ".json"]

    @staticmethod
    def _get_default_path() -> Path:
        """Finds edmate_config in the project root."""
        # Look for config in the project root relative to this file
        # config_loader.py is in content_gen/core/
        root_path = Path(__file__).parent.parent.parent
        
        # Try different extensions
        for ext in ConfigLoader.SUPPORTED_EXTENSIONS:
            path = root_path / f"{ConfigLoader.DEFAULT_CONFIG_NAME}{ext}"
            if path.exists():
                return path
        
        # Return default yaml path if none found
        return root_path / f"{ConfigLoader.DEFAULT_CONFIG_NAME}.yaml"

    @staticmethod
    def load_config(config_path: Optional[Union[str, Path]] = None) -> EdmateConfig:
        """
        Loads configuration from a file (YAML or JSON) and validates it.
        If config_path is None, it searches for default config files in the project root.
        """
        if config_path is None:
            path = ConfigLoader._get_default_path()
        else:
            path = Path(config_path)

        if not path.exists():
            print(f"ℹ️ Config file {path} not found. Using default settings.")
            return EdmateConfig()

        try:
            with open(path, 'r') as f:
                if path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif path.suffix == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {path.suffix}")

            if not data:
                return EdmateConfig()

            return EdmateConfig(**data)

        except ValidationError as e:
            print(f"❌ Configuration validation failed for {path}:")
            for error in e.errors():
                loc = " -> ".join(str(l) for l in error['loc'])
                print(f"  - {loc}: {error['msg']}")
            print("⚠️ Using default settings due to validation errors.")
            return EdmateConfig()
            
        except Exception as e:
            print(f"⚠️ Error loading config from {path}: {e}")
            print("⚠️ Using default settings.")
            return EdmateConfig()

    @staticmethod
    def save_template(path: Union[str, Path] = "edmate_config.json.example", format: str = "json"):
        """Saves a template configuration file in the specified format."""
        config = EdmateConfig()
        # Convert to dict, using by_alias if necessary, but here we use the field names
        data = config.dict()
        
        path = Path(path)
        with open(path, 'w') as f:
            if format.lower() == "json":
                json.dump(data, f, indent=2)
            elif format.lower() in ["yaml", "yml"]:
                yaml.dump(data, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
        
        print(f"✅ Template config saved to {path}")
