import os
import yaml
from content_gen.core.config import CoreConfig
from content_gen.core.config_schema import EdmateConfig


def test_config_load_defaults():
    """Verifies that the config loader returns defaults when no file exists."""
    config = CoreConfig.load_from_yaml("non_existent_config.yaml")
    assert isinstance(config, EdmateConfig)
    assert config.budget.max_daily_usd == 10.0  # default
    assert config.extraction_settings.min_question_number == 1
    # No YAML → no ceiling; runtime/API may still set a cap when provided.
    assert config.extraction_settings.max_question_number is None
    assert config.extraction_settings.question_detection_mode == "balanced"


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
    assert config.model_routing.extraction == "test/model"
    assert config.budget.max_daily_usd == 50.0
    assert config.extraction_settings.min_question_number == 2
    assert config.extraction_settings.max_question_number == 120
    assert config.extraction_settings.question_detection_mode == "open"

