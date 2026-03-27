import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from nanobot.cli.commands import app
from nanobot.config.schema import Config

runner = CliRunner()


def _save_config(config: Config, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.model_dump(by_alias=True)), encoding="utf-8")


def test_fitness_cli_flow(tmp_path):
    config_path = tmp_path / "instance" / "config.json"
    workspace_path = tmp_path / "workspace"
    config = Config()
    config.agents.defaults.workspace = str(workspace_path)
    _save_config(config, config_path)

    with patch("nanobot.config.loader.get_config_path", lambda: config_path):
        result = runner.invoke(
            app,
            [
                "fitness",
                "profile-set",
                "--user-id",
                "demo",
                "--gender",
                "男",
                "--age",
                "23",
                "--height",
                "176",
                "--weight",
                "70",
                "--goal",
                "薄肌增肌",
                "--experience-level",
                "初级",
                "--training-days-per-week",
                "4",
                "--session-duration",
                "60",
                "--environment",
                "家里",
                "--diet-constraint",
                "外卖为主",
            ],
        )
        assert result.exit_code == 0
        assert "Profile saved" in result.stdout

        result = runner.invoke(app, ["fitness", "plan-generate", "--user-id", "demo", "--week-start", "2026-03-25"])
        assert result.exit_code == 0
        assert "Weekly plan generated" in result.stdout
        assert "周一" in result.stdout

        result = runner.invoke(
            app,
            [
                "fitness",
                "feedback-add",
                "--user-id",
                "demo",
                "--date",
                "2026-03-25",
                "--trained",
                "--completed-exercises",
                "俯卧撑,单臂哑铃划船",
                "--completion-rate",
                "0.8",
                "--fatigue-level",
                "4",
                "--diet-adherence",
                "基本达标",
            ],
        )
        assert result.exit_code == 0
        assert "Feedback saved" in result.stdout

        result = runner.invoke(app, ["fitness", "feedback-show", "--user-id", "demo"])
        assert result.exit_code == 0
        assert "2026-03-25" in result.stdout


def test_fitness_adjustment_requires_feedback(tmp_path):
    config_path = tmp_path / "instance" / "config.json"
    workspace_path = tmp_path / "workspace"
    config = Config()
    config.agents.defaults.workspace = str(workspace_path)
    _save_config(config, config_path)

    with patch("nanobot.config.loader.get_config_path", lambda: config_path):
        runner.invoke(
            app,
            [
                "fitness",
                "profile-set",
                "--user-id",
                "demo",
                "--gender",
                "女",
                "--age",
                "25",
                "--height",
                "165",
                "--weight",
                "55",
                "--goal",
                "新手入门",
                "--experience-level",
                "新手",
                "--training-days-per-week",
                "3",
                "--session-duration",
                "45",
                "--environment",
                "宿舍",
                "--diet-constraint",
                "无",
            ],
        )
        result = runner.invoke(app, ["fitness", "adjustment-generate", "--user-id", "demo"])
        assert result.exit_code == 1
        assert "至少需要一条反馈记录" in result.stdout
