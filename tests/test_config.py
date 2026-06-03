import pytest
import yaml
from jsonschema import ValidationError, validate

from octobell.config import _CONFIG_SCHEMA, AccountConfig


def _minimal_imap():
    return {"host": "imap.example.com", "user": "u@example.com", "password": "secret"}


def _write_yaml(tmp_path, data, name="test.yml"):
    p = tmp_path / name
    p.write_text(yaml.dump(data))
    return p


class TestConfigSchema:
    def test_minimal_valid(self):
        validate({"imap": _minimal_imap()}, _CONFIG_SCHEMA)

    def test_full_valid(self):
        validate(
            {
                "imap": {**_minimal_imap(), "port": 993, "folders": ["INBOX", "GitHub"]},
                "notification": {"subtitle": "{sender}", "message": "{title}"},
                "rules": {
                    "default": [{"reason": "ci_activity", "action": "skip"}],
                    "orgs": {
                        "myorg": {
                            "match": [{"reason": "comment", "action": "notify"}],
                            "repos": {
                                "myrepo": [{"reason": "mention", "action": "skip", "event": "comment"}],
                            },
                        },
                    },
                },
            },
            _CONFIG_SCHEMA,
        )

    def test_missing_imap(self):
        with pytest.raises(ValidationError, match="'imap' is a required property"):
            validate({}, _CONFIG_SCHEMA)

    def test_missing_imap_host(self):
        data = {"imap": {"user": "u", "password": "p"}}
        with pytest.raises(ValidationError, match="'host' is a required property"):
            validate(data, _CONFIG_SCHEMA)

    def test_empty_host(self):
        data = {"imap": {"host": "", "user": "u", "password": "p"}}
        with pytest.raises(ValidationError):
            validate(data, _CONFIG_SCHEMA)

    def test_unknown_top_level_key(self):
        data = {"imap": _minimal_imap(), "bogus": True}
        with pytest.raises(ValidationError, match="Additional properties are not allowed"):
            validate(data, _CONFIG_SCHEMA)

    def test_unknown_imap_key(self):
        data = {"imap": {**_minimal_imap(), "typo": 1}}
        with pytest.raises(ValidationError, match="Additional properties are not allowed"):
            validate(data, _CONFIG_SCHEMA)

    def test_invalid_port_type(self):
        data = {"imap": {**_minimal_imap(), "port": "993"}}
        with pytest.raises(ValidationError):
            validate(data, _CONFIG_SCHEMA)

    def test_port_zero(self):
        data = {"imap": {**_minimal_imap(), "port": 0}}
        with pytest.raises(ValidationError):
            validate(data, _CONFIG_SCHEMA)

    def test_folders_as_string(self):
        validate({"imap": {**_minimal_imap(), "folders": "INBOX"}}, _CONFIG_SCHEMA)

    def test_folders_as_list(self):
        validate({"imap": {**_minimal_imap(), "folders": ["INBOX", "Archive"]}}, _CONFIG_SCHEMA)

    def test_empty_folders_list(self):
        data = {"imap": {**_minimal_imap(), "folders": []}}
        with pytest.raises(ValidationError):
            validate(data, _CONFIG_SCHEMA)

    def test_invalid_reason_enum(self):
        data = {"imap": _minimal_imap(), "rules": {"default": [{"reason": "bogus"}]}}
        with pytest.raises(ValidationError, match="'bogus' is not one of"):
            validate(data, _CONFIG_SCHEMA)

    def test_invalid_action_enum(self):
        data = {"imap": _minimal_imap(), "rules": {"default": [{"reason": "comment", "action": "ignore"}]}}
        with pytest.raises(ValidationError, match="'ignore' is not one of"):
            validate(data, _CONFIG_SCHEMA)

    def test_invalid_event_enum(self):
        data = {"imap": _minimal_imap(), "rules": {"default": [{"reason": "comment", "event": "nope"}]}}
        with pytest.raises(ValidationError, match="'nope' is not one of"):
            validate(data, _CONFIG_SCHEMA)

    def test_rule_missing_reason(self):
        data = {"imap": _minimal_imap(), "rules": {"default": [{"action": "skip"}]}}
        with pytest.raises(ValidationError, match="'reason' is a required property"):
            validate(data, _CONFIG_SCHEMA)

    def test_unknown_rule_key(self):
        data = {"imap": _minimal_imap(), "rules": {"default": [{"reason": "comment", "extra": 1}]}}
        with pytest.raises(ValidationError, match="Additional properties are not allowed"):
            validate(data, _CONFIG_SCHEMA)


class TestAccountConfigFromYaml:
    def test_minimal(self, tmp_path):
        path = _write_yaml(tmp_path, {"imap": _minimal_imap()})
        cfg = AccountConfig.from_yaml(path)
        assert cfg.imap_host == "imap.example.com"
        assert cfg.imap_user == "u@example.com"
        assert cfg.imap_port == 993
        assert cfg.imap_folders == ("INBOX",)
        assert cfg.notification_subtitle_format == "{sender} {action} on {repo}"
        assert cfg.notification_message_format == "{title}"

    def test_custom_port_and_folders(self, tmp_path):
        data = {"imap": {**_minimal_imap(), "port": 143, "folders": ["GitHub", "Work"]}}
        cfg = AccountConfig.from_yaml(_write_yaml(tmp_path, data))
        assert cfg.imap_port == 143
        assert cfg.imap_folders == ("GitHub", "Work")

    def test_folders_string_normalized(self, tmp_path):
        data = {"imap": {**_minimal_imap(), "folders": "Archive"}}
        cfg = AccountConfig.from_yaml(_write_yaml(tmp_path, data))
        assert cfg.imap_folders == ("Archive",)

    def test_notification_formats(self, tmp_path):
        data = {
            "imap": _minimal_imap(),
            "notification": {"subtitle": "[{repo}] {sender}", "message": "{title} ({reason})"},
        }
        cfg = AccountConfig.from_yaml(_write_yaml(tmp_path, data))
        assert cfg.notification_subtitle_format == "[{repo}] {sender}"
        assert cfg.notification_message_format == "{title} ({reason})"

    def test_rules_parsed(self, tmp_path):
        data = {
            "imap": _minimal_imap(),
            "rules": {"default": [{"reason": "ci_activity", "action": "skip"}]},
        }
        cfg = AccountConfig.from_yaml(_write_yaml(tmp_path, data))
        assert len(cfg.rules.default_rules) == 1
        assert cfg.rules.default_rules[0].reason.value == "ci_activity"

    def test_invalid_yaml(self, tmp_path):
        p = tmp_path / "bad.yml"
        p.write_text(": :\n  - ][")
        with pytest.raises(ValueError, match="invalid YAML"):
            AccountConfig.from_yaml(p)

    def test_schema_error_surfaces(self, tmp_path):
        path = _write_yaml(tmp_path, {"imap": {"user": "u", "password": "p"}})
        with pytest.raises(ValueError, match="'host' is a required property"):
            AccountConfig.from_yaml(path)

    def test_account_name_from_filename(self, tmp_path):
        path = _write_yaml(tmp_path, {"imap": _minimal_imap()}, name="work.yml")
        cfg = AccountConfig.from_yaml(path)
        assert cfg.name == "work"
