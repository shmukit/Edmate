import pytest
import yaml
import json
from pathlib import Path
from content_gen.core.config_loader import ConfigLoader
from content_gen.core.config_schema import EdmateConfig

@pytest.fixture
def temp_config_dir(tmp_path):
    return tmp_path

def test_load_config_yaml(temp_config_dir):
    yaml_content = {
        "model_routing": {
            "extraction": "test-extraction-model",
            "generation": "test-generation-model"
        },
        "budget": {
            "max_daily_usd": 50.0
        }
    }
    config_path = temp_config_dir / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(yaml_content, f)
    
    config = ConfigLoader.load_config(config_path)
    assert config.model_routing.extraction == "test-extraction-model"
    assert config.model_routing.generation == "test-generation-model"
    assert config.budget.max_daily_usd == 50.0

def test_load_config_json(temp_config_dir):
    json_content = {
        "model_routing": {
            "extraction": "json-extraction-model"
        },
        "learning_science": {
            "profile": "advanced"
        }
    }
    config_path = temp_config_dir / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(json_content, f)
    
    config = ConfigLoader.load_config(config_path)
    assert config.model_routing.extraction == "json-extraction-model"
    assert config.learning_science.profile == "advanced"

def test_load_config_not_found():
    # Should return default config if file not found
    config = ConfigLoader.load_config("non_existent_config.yaml")
    assert isinstance(config, EdmateConfig)
    assert config.model_routing.extraction == "gemini/gemini-1.5-pro" # default

def test_load_config_invalid_yaml(temp_config_dir):
    # Invalid YAML (missing required fields or wrong types - though Pydantic handles defaults)
    yaml_content = "model_routing: [this is not a dict]"
    config_path = temp_config_dir / "invalid_config.yaml"
    with open(config_path, "w") as f:
        f.write(yaml_content)
    
    # Should return defaults if validation fails
    config = ConfigLoader.load_config(config_path)
    assert isinstance(config, EdmateConfig)
    assert config.model_routing.extraction == "gemini/gemini-1.5-pro"

def test_load_config_validation_error(temp_config_dir):
    # Wrong type for budget
    json_content = {
        "budget": {
            "max_daily_usd": "not-a-number"
        }
    }
    config_path = temp_config_dir / "error_config.json"
    with open(config_path, "w") as f:
        json.dump(json_content, f)
    
    config = ConfigLoader.load_config(config_path)
    assert config.budget.max_daily_usd == 10.0 # default value
