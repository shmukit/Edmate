import os
import yaml
from content_gen.core.config import CoreConfig
from content_gen.core.schemas import ModelConfig


def test_config_load_defaults():
    """Verifies that the config loader returns defaults when no file exists."""
    config = CoreConfig.load_from_yaml("non_existent_config.yaml")
    assert isinstance(config, ModelConfig)
    assert config.max_budget == 10.0  # default
    assert config.min_question_number == 1
    assert config.max_question_number == 40
    assert config.question_detection_mode == "balanced"


def test_config_load_valid_yaml(tmp_path):
    """Verifies that the config loader correctly parses a YAML file."""
    config_file = tmp_path / "test_config.yaml"
    data = {
        "model_routing": {
            "extraction": "test/model",
            "generation": "test/gen"
        },
        "budget": {
            "max_daily_usd": 50.0
        },
        "extraction_settings": {
            "min_question_number": 2,
            "max_question_number": 120,
            "question_detection_mode": "open"
        }
    }
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    config = CoreConfig.load_from_yaml(str(config_file))
    assert config.extraction_model == "test/model"
    assert config.max_budget == 50.0
    assert config.min_question_number == 2
    assert config.max_question_number == 120
    assert config.question_detection_mode == "open"
