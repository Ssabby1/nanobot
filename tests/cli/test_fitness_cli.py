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
                "\u7537",
                "--age",
                "23",
                "--height",
                "176",
                "--weight",
                "70",
                "--goal",
                "\u589e\u808c",
                "--experience-level",
                "\u521d\u7ea7",
                "--training-days-per-week",
                "4",
                "--session-duration",
                "60",
                "--environment",
                "\u5bb6\u91cc",
                "--diet-constraint",
                "\u5916\u5356\u4e3a\u4e3b",
            ],
        )
        assert result.exit_code == 0
        assert "Profile saved" in result.stdout

        result = runner.invoke(app, ["fitness", "plan-generate", "--user-id", "demo", "--week-start", "2026-03-25"])
        assert result.exit_code == 0
        assert "Weekly plan generated" in result.stdout
        assert "\u5468\u4e00" in result.stdout

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
                "\u5367\u63a8,\u5355\u81c2\u54d1\u94c3\u5212\u8239",
                "--completion-rate",
                "0.8",
                "--fatigue-level",
                "4",
                "--diet-adherence",
                "\u57fa\u672c\u8fbe\u6807",
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
                "\u5973",
                "--age",
                "25",
                "--height",
                "165",
                "--weight",
                "55",
                "--goal",
                "\u65b0\u624b\u5165\u95e8",
                "--experience-level",
                "\u65b0\u624b",
                "--training-days-per-week",
                "3",
                "--session-duration",
                "45",
                "--environment",
                "\u5bbf\u820d",
                "--diet-constraint",
                "\u65e0",
            ],
        )
        result = runner.invoke(app, ["fitness", "adjustment-generate", "--user-id", "demo"])
        assert result.exit_code == 1
        assert "\u81f3\u5c11\u9700\u8981\u4e00\u6761\u53cd\u9988\u8bb0\u5f55" in result.stdout


def test_fitness_route_natural_language_flow(tmp_path):
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
                "route",
                "\u5e2e\u6211\u5efa\u6863\uff0c\u6211\u662f\u7537\uff0c23\u5c81\uff0c176cm\uff0c70kg\uff0c"
                "\u76ee\u6807\u662f\u589e\u808c\uff0c\u521d\u7ea7\uff0c\u6bcf\u54684\u6b21\uff0c"
                "\u6bcf\u6b2160\u5206\u949f\uff0c\u5728\u5bb6\u8bad\u7ec3\uff0c\u5916\u5356\u4e3a\u4e3b",
                "--user-id",
                "demo",
            ],
        )
        assert result.exit_code == 0
        assert "\u5df2\u5b8c\u6210\u5efa\u6863" in result.stdout

        result = runner.invoke(app, ["fitness", "route", "\u7ed9\u6211\u751f\u6210\u8fd9\u5468\u8bad\u7ec3\u8ba1\u5212", "--user-id", "demo"])
        assert result.exit_code == 0
        assert "\u5df2\u751f\u6210\u672c\u5468\u8ba1\u5212" in result.stdout

        result = runner.invoke(
            app,
            [
                "fitness",
                "route",
                "\u6211\u4eca\u5929\u7ec3\u4e86\u5367\u63a8\u548c\u5212\u8239\uff0c\u5b8c\u6210\u5ea680%\uff0c"
                "\u6709\u70b9\u7d2f\uff0c\u996e\u98df\u8fd8\u884c",
                "--user-id",
                "demo",
            ],
        )
        assert result.exit_code == 0
        assert "\u5df2\u8bb0\u5f55\u4eca\u65e5\u6253\u5361" in result.stdout

        result = runner.invoke(app, ["fitness", "route", "\u770b\u770b\u6253\u5361\u8bb0\u5f55", "--user-id", "demo"])
        assert result.exit_code == 0
        assert "\u6253\u5361\u8bb0\u5f55" in result.stdout


def test_fitness_route_reports_missing_fields(tmp_path):
    config_path = tmp_path / "instance" / "config.json"
    workspace_path = tmp_path / "workspace"
    config = Config()
    config.agents.defaults.workspace = str(workspace_path)
    _save_config(config, config_path)

    with patch("nanobot.config.loader.get_config_path", lambda: config_path):
        result = runner.invoke(app, ["fitness", "route", "\u5e2e\u6211\u5efa\u6863\uff0c\u6211\u662f\u7537\uff0c23\u5c81", "--user-id", "demo"])
        assert result.exit_code == 0
        assert "\u8fd8\u7f3a\u5c11\u8fd9\u4e9b\u4fe1\u606f" in result.stdout


def test_fitness_route_can_extract_user_id_from_message(tmp_path):
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
                "route",
                "\u6211\u53ebsasa\uff0c\u6211\u662f\u7537\uff0c23\u5c81\uff0c176cm\uff0c70kg\uff0c"
                "\u76ee\u6807\u662f\u589e\u808c\uff0c\u521d\u7ea7\uff0c\u6bcf\u54684\u6b21\uff0c"
                "\u6bcf\u6b2160\u5206\u949f\uff0c\u5728\u5bb6\u8bad\u7ec3\uff0c\u5916\u5356\u4e3a\u4e3b",
            ],
        )
        assert result.exit_code == 0
        assert "\u7528\u6237: sasa" in result.stdout


def test_agent_single_message_can_short_circuit_to_fitness_router(tmp_path):
    config_path = tmp_path / "instance" / "config.json"
    workspace_path = tmp_path / "workspace"
    config = Config()
    config.agents.defaults.workspace = str(workspace_path)
    _save_config(config, config_path)

    with patch("nanobot.config.loader.get_config_path", lambda: config_path):
        result = runner.invoke(
            app,
            [
                "agent",
                "-m",
                "\u6211\u53ebsasa\uff0c\u6211\u662f\u7537\uff0c23\u5c81\uff0c176cm\uff0c70kg\uff0c"
                "\u76ee\u6807\u662f\u589e\u808c\uff0c\u521d\u7ea7\uff0c\u6bcf\u54684\u6b21\uff0c"
                "\u6bcf\u6b2160\u5206\u949f\uff0c\u5728\u5bb6\u8bad\u7ec3\uff0c\u5916\u5356\u4e3a\u4e3b",
            ],
        )
        assert result.exit_code == 0
        assert "\u7528\u6237: sasa" in result.stdout


def test_agent_single_message_remembers_last_fitness_user(tmp_path):
    config_path = tmp_path / "instance" / "config.json"
    workspace_path = tmp_path / "workspace"
    config = Config()
    config.agents.defaults.workspace = str(workspace_path)
    _save_config(config, config_path)

    with patch("nanobot.config.loader.get_config_path", lambda: config_path):
        runner.invoke(
            app,
            [
                "agent",
                "-m",
                "\u6211\u53ebsasa\uff0c\u6211\u662f\u7537\uff0c23\u5c81\uff0c176cm\uff0c70kg\uff0c"
                "\u76ee\u6807\u662f\u589e\u808c\uff0c\u521d\u7ea7\uff0c\u6bcf\u54684\u6b21\uff0c"
                "\u6bcf\u6b2160\u5206\u949f\uff0c\u5728\u5bb6\u8bad\u7ec3\uff0c\u5916\u5356\u4e3a\u4e3b",
            ],
        )
        result = runner.invoke(app, ["agent", "-m", "\u7ed9\u6211\u770b\u770b\u6211\u7684\u753b\u50cf"])
        assert result.exit_code == 0
        assert "\u7528\u6237: sasa" in result.stdout
