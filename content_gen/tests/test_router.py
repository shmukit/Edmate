import pytest
from unittest.mock import MagicMock, patch
from content_gen.core.model_router import ModelRoutingEngine, BudgetExceededError
from content_gen.core.config_schema import EdmateConfig, ModelRouting, BudgetConfig


def test_router_budget_check():
    """Verifies that the Economic Kill-Switch prevents calls when budget is exceeded."""
    config = EdmateConfig(budget=BudgetConfig(max_daily_usd=0.1))  # low budget
    router = ModelRoutingEngine(config=config)

    # Mock metrics to show high cost
    router.tracker.metrics["total_cost"] = 0.5

    with pytest.raises(BudgetExceededError):
        router.generate_content("Hello")


@patch("litellm.completion")
def test_router_task_routing(mock_completion):
    """Verifies that the router selects the correct model for the task."""
    config = EdmateConfig(
        model_routing=ModelRouting(
            extraction="test/extraction",
            generation="test/generation"
        )
    )
    router = ModelRoutingEngine(config=config)

    # Mock response with serializable usage data
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "response"
    mock_resp.usage = MagicMock()
    mock_resp.usage.get.side_effect = lambda k, d=0: {
        "total_tokens": 100}.get(k, d)
    mock_resp.usage.total_tokens = 100
    mock_resp._response_ms = 100

    # Mock the tracker.log_usage to avoid JSON issues with MagicMock in simple unit tests
    router.tracker.log_usage = MagicMock()

    mock_completion.return_value = mock_resp

    # Test extraction task - Expect simple string content when no images are present
    router.generate_content("extract this", task_type="extraction")
    mock_completion.assert_called_with(
        model="test/extraction",
        messages=[{"role": "user", "content": "extract this"}],
        timeout=120,
    )

    # Test default generation task
    router.generate_content("generate this")
    mock_completion.assert_called_with(
        model="test/generation",
        messages=[{"role": "user", "content": "generate this"}],
        timeout=180,
    )

