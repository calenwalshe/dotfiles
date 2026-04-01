"""Tests for openclaw deployment config and Slack adapter."""

import pytest

from src.deploy.openclaw_config import OpenClawConfig
from src.integrations.slack_adapter import SlackAdapter


class TestOpenClawConfig:
    def test_local_dev_config(self):
        config = OpenClawConfig.for_local_dev()
        assert str(config.workspace_dir) == "."
        assert str(config.artifact_store_dir) == "artifacts"

    def test_verify_local_dev(self):
        config = OpenClawConfig.for_local_dev()
        checks = config.verify()
        assert checks["workspace_exists"] is True  # "." always exists
        assert "claude_available" in checks

    def test_default_container_paths(self):
        config = OpenClawConfig()
        assert "openclaw" in str(config.workspace_dir)
        assert "openclaw" in str(config.artifact_store_dir)


class TestSlackAdapter:
    def test_requires_bot_token(self):
        with pytest.raises(ValueError, match="SLACK_BOT_TOKEN"):
            SlackAdapter(bot_token="", channel_id="C123")

    def test_requires_channel_id(self):
        with pytest.raises(ValueError, match="SLACK_CHANNEL_ID"):
            SlackAdapter(bot_token="xoxb-test", channel_id="")

    def test_constructs_with_valid_args(self):
        adapter = SlackAdapter(bot_token="xoxb-test", channel_id="C123")
        assert adapter.bot_token == "xoxb-test"
        assert adapter.channel_id == "C123"
