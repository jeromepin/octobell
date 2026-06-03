import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import ValidationError, validate

from octobell.rules import RulesConfig

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "octobell"

_REASONS = [
    "assign",
    "author",
    "comment",
    "invitation",
    "manual",
    "mention",
    "review_requested",
    "security_alert",
    "state_change",
    "subscribed",
    "team_mention",
    "ci_activity",
    "unknown",
]

_EVENTS = [
    "comment",
    "approved",
    "changes_requested",
    "merged",
    "closed",
    "reopened",
    "push",
    "review_dismissed",
    "pr_opened",
    "review_requested",
    "unknown",
]

_RULE_SCHEMA = {
    "type": "object",
    "required": ["reason"],
    "additionalProperties": False,
    "properties": {
        "reason": {"type": "string", "enum": _REASONS},
        "action": {"type": "string", "enum": ["notify", "skip"]},
        "event": {"type": "string", "enum": _EVENTS},
    },
}

_ORG_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "match": {
            "type": "array",
            "items": _RULE_SCHEMA,
        },
        "repos": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": _RULE_SCHEMA,
            },
        },
    },
}

_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["imap"],
    "additionalProperties": False,
    "properties": {
        "imap": {
            "type": "object",
            "required": ["host", "user", "password"],
            "additionalProperties": False,
            "properties": {
                "host": {"type": "string", "minLength": 1},
                "user": {"type": "string", "minLength": 1},
                "password": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1},
                "folders": {
                    "oneOf": [
                        {"type": "string", "minLength": 1},
                        {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
                    ],
                },
            },
        },
        "notification": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "subtitle": {"type": "string", "minLength": 1},
                "message": {"type": "string", "minLength": 1},
            },
        },
        "rules": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "default": {
                    "type": "array",
                    "items": _RULE_SCHEMA,
                },
                "orgs": {
                    "type": "object",
                    "additionalProperties": _ORG_SCHEMA,
                },
            },
        },
    },
}


@dataclass(frozen=True)
class AccountConfig:
    name: str
    imap_host: str
    imap_user: str
    imap_password: str
    imap_port: int = 993
    imap_folders: tuple[str, ...] = ("INBOX",)
    idle_timeout_seconds: int = 28 * 60
    reconnect_max_backoff_seconds: int = 300
    notification_timeout_seconds: int = 10
    notification_subtitle_format: str = "{sender} {action} on {repo}"
    notification_message_format: str = "{title}"
    rules: RulesConfig = field(default_factory=RulesConfig.empty)

    @classmethod
    def from_yaml(cls, path: Path) -> "AccountConfig":
        logger.info(f"Loading config from {path}")

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"{path.name}: invalid YAML: {e}") from e

        try:
            validate(data, _CONFIG_SCHEMA)
        except ValidationError as e:
            raise ValueError(
                f"{path.name}: {e.message} (at {'.'.join(str(p) for p in e.absolute_path) or 'root'})"
            ) from e

        imap = data["imap"]
        port = imap.get("port", 993)

        folders_raw = imap.get("folders", ["INBOX"])
        if isinstance(folders_raw, str):
            folders_raw = [folders_raw]
        folders = tuple(folders_raw)

        rules = RulesConfig.from_dict(data.get("rules", {}))

        notification = data.get("notification", {})
        subtitle_format = notification.get("subtitle", "{sender} {action} on {repo}")
        message_format = notification.get("message", "{title}")

        logger.info(f"  account: {path.stem}")
        logger.info(f"  imap: {imap['host']}:{port} as {imap['user']}")
        logger.info(f"  folders: {', '.join(folders)}")
        _log_rules(path.stem, rules)

        return cls(
            name=path.stem,
            imap_host=imap["host"],
            imap_port=port,
            imap_user=imap["user"],
            imap_password=imap["password"],
            imap_folders=folders,
            notification_subtitle_format=subtitle_format,
            notification_message_format=message_format,
            rules=rules,
        )


def load_accounts(config_dir: Path = CONFIG_DIR) -> list[AccountConfig]:
    config_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Config directory: {config_dir}")

    files = sorted(config_dir.glob("*.yml"))
    if not files:
        _create_default_config(config_dir / "default.yml")
        print(f"Created example config at {config_dir / 'default.yml'}")
        print("Edit it with your IMAP credentials, then run octobell again.")
        sys.exit(0)

    logger.info(f"Found {len(files)} config file(s): {', '.join(p.name for p in files)}")

    accounts = []
    for path in files:
        accounts.append(AccountConfig.from_yaml(path))

    return accounts


def _format_rule(rule) -> str:
    event_part = f" [{rule.event.value}]" if rule.event else ""
    return f"{rule.reason.value}{event_part} → {rule.action.value}"


def _log_rules(account_name: str, rules: RulesConfig) -> None:
    if not rules.default_rules and not rules.org_rules and not rules.repo_rules:
        logger.info("  rules: none (all notifications will fire)")
        return

    if rules.default_rules:
        for rule in rules.default_rules:
            logger.info(f"  rule: default — {_format_rule(rule)}")

    for org, org_rule_list in rules.org_rules.items():
        for rule in org_rule_list:
            logger.info(f"  rule: {org}/* — {_format_rule(rule)}")

    for org, repos in rules.repo_rules.items():
        for repo, repo_rule_list in repos.items():
            for rule in repo_rule_list:
                logger.info(f"  rule: {org}/{repo} — {_format_rule(rule)}")


_DEFAULT_CONFIG_TEMPLATE = """\
# octobell account configuration
#
# Each .yml file in ~/.config/octobell/ defines one IMAP account.
# octobell watches all accounts simultaneously.

imap:
  host: imap.gmail.com
  port: 993
  user: you@gmail.com
  password: xxxx-xxxx-xxxx-xxxx
  folders:
    - INBOX

# Rules control which GitHub notifications fire and which are silently consumed.
# Default behavior (no rule match) is: notify.
#
# Actions:
#   notify — display a desktop notification, mark email as read
#   skip   — mark email as read silently (no notification)
#
# Available reasons (from X-GitHub-Reason header):
#   author, review_requested, comment, mention, team_mention,
#   assign, subscribed, state_change, ci_activity
#
# Optional event filter (what happened, parsed from email body):
#   comment, approved, changes_requested, merged, closed,
#   reopened, push, review_dismissed
#   Omit to match any event for that reason.
#
# Evaluation order (first match wins):
#   1. orgs.<org>.repos.<repo>  (most specific)
#   2. orgs.<org>.match         (org-level)
#   3. default                  (global)
#   4. implicit notify          (if nothing matches)

# Notification display settings.
# Both subtitle and message support these template variables:
#   {sender}     — GitHub username
#   {action}     — action text (e.g. "commented", "requested your review")
#   {title}      — PR/issue title
#   {repo}       — full repo name (owner/name)
#   {repo_owner} — repo owner
#   {repo_name}  — repo name
#   {reason}     — raw reason (e.g. review_requested, comment)
#
# notification:
#   subtitle: "{sender} {action} on {repo}"
#   message: "{title}"

rules:
  default: []
    # - reason: ci_activity
    #   action: skip
    # - reason: review_requested
    #   event: comment
    #   action: skip

  # orgs:
  #   myorg:
  #     match:
  #       - reason: state_change
  #         action: skip
  #     repos:
  #       noisy-repo:
  #         - reason: comment
  #           action: skip
"""


def _create_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_DEFAULT_CONFIG_TEMPLATE)
