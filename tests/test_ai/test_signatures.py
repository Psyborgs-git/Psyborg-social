from __future__ import annotations

import pytest


def test_dspy_import():
    try:
        import dspy
        assert dspy is not None
    except ImportError:
        pytest.skip("dspy-ai not installed")


def test_ai_config_import():
    from socialmind.ai.config import configure_dspy
    assert callable(configure_dspy)


def test_content_module_import():
    from socialmind.ai.modules.content import ContentGenerator
    assert ContentGenerator is not None


def test_post_pipeline_import():
    from socialmind.ai.pipelines.post_pipeline import PostCampaignPipeline
    assert PostCampaignPipeline is not None
