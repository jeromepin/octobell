import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from octobell.rules import RulesConfig

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "octobell"


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
    rules: RulesConfig = None

    def __post_init__(self):
        if self.rules is None:
            object.__setattr__(self, "rules", RulesConfig.empty())

    @classmethod
    def from_yaml(cls, path: Path) -> "AccountConfig":
        logger.info(f"Loading config from {path}")

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"{path.name}: invalid YAML: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: expected a YAML mapping, got {type(data).__name__}")

        if "imap" not in data:
            raise ValueError(f"{path.name}: missing 'imap' section")

        imap = data["imap"]
        if not isinstance(imap, dict):
            raise ValueError(f"{path.name}: 'imap' must be a mapping, got {type(imap).__name__}")

        for key in ("host", "user", "password"):
            if key not in imap:
                raise ValueError(f"{path.name}: missing required field 'imap.{key}'")
            if not isinstance(imap[key], str) or not imap[key].strip():
                raise ValueError(f"{path.name}: 'imap.{key}' must be a non-empty string")

        port = imap.get("port", 993)
        if not isinstance(port, int) or port <= 0:
            raise ValueError(f"{path.name}: 'imap.port' must be a positive integer, got {port!r}")

        folders_raw = imap.get("folders", ["INBOX"])
        if isinstance(folders_raw, str):
            folders_raw = [folders_raw]
        if not isinstance(folders_raw, list):
            raise ValueError(f"{path.name}: 'imap.folders' must be a string or list, got {type(folders_raw).__name__}")
        folders = tuple(f.strip() for f in folders_raw if isinstance(f, str) and f.strip())
        if not folders:
            raise ValueError(f"{path.name}: 'imap.folders' must contain at least one folder")

        unknown_imap_keys = set(imap.keys()) - {"host", "port", "user", "password", "folders"}
        if unknown_imap_keys:
            logger.warning(f"{path.name}: unknown key(s) in 'imap': {', '.join(sorted(unknown_imap_keys))}")

        unknown_top_keys = set(data.keys()) - {"imap", "rules", "notification"}
        if unknown_top_keys:
            logger.warning(f"{path.name}: unknown top-level key(s): {', '.join(sorted(unknown_top_keys))}")

        rules_data = data.get("rules", {})
        if rules_data and not isinstance(rules_data, dict):
            raise ValueError(f"{path.name}: 'rules' must be a mapping, got {type(rules_data).__name__}")

        rules = RulesConfig.from_dict(rules_data)

        notification_data = data.get("notification", {})
        if notification_data and not isinstance(notification_data, dict):
            raise ValueError(f"{path.name}: 'notification' must be a mapping, got {type(notification_data).__name__}")
        notification_fields = notification_data or {}
        subtitle_format = notification_fields.get("subtitle", "{sender} {action} on {repo}")
        if not isinstance(subtitle_format, str) or not subtitle_format.strip():
            raise ValueError(f"{path.name}: 'notification.subtitle' must be a non-empty string")
        message_format = notification_fields.get("message", "{title}")
        if not isinstance(message_format, str) or not message_format.strip():
            raise ValueError(f"{path.name}: 'notification.message' must be a non-empty string")

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
