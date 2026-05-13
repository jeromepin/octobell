import logging
from dataclasses import dataclass, field
from enum import Enum, unique
from pathlib import Path

import yaml

from octobell.enums import NotificationReason
from octobell.models import GitHubEmail

logger = logging.getLogger(__name__)


@unique
class Action(str, Enum):
    NOTIFY = "notify"
    SKIP = "skip"


@dataclass(frozen=True)
class Rule:
    reason: NotificationReason
    action: Action


@dataclass
class RulesConfig:
    default_rules: list[Rule] = field(default_factory=list)
    org_rules: dict[str, list[Rule]] = field(default_factory=dict)
    repo_rules: dict[str, dict[str, list[Rule]]] = field(default_factory=dict)

    def evaluate(self, email: GitHubEmail) -> Action:
        org = email.repo_owner
        repo = email.repo_name

        if org in self.repo_rules and repo in self.repo_rules[org]:
            for rule in self.repo_rules[org][repo]:
                if rule.reason == email.reason:
                    return rule.action

        if org in self.org_rules:
            for rule in self.org_rules[org]:
                if rule.reason == email.reason:
                    return rule.action

        for rule in self.default_rules:
            if rule.reason == email.reason:
                return rule.action

        return Action.NOTIFY

    @classmethod
    def empty(cls) -> "RulesConfig":
        return cls()

    @classmethod
    def load(cls, path: Path) -> "RulesConfig":
        if not path.exists():
            _create_default_rules_file(path)
            return cls.empty()

        with open(path) as f:
            data = yaml.safe_load(f)

        if not data:
            return cls.empty()

        default_rules = _parse_rules(data.get("default", []))

        org_rules: dict[str, list[Rule]] = {}
        repo_rules: dict[str, dict[str, list[Rule]]] = {}

        for org_name, org_data in data.get("rules", {}).items():
            if not isinstance(org_data, dict):
                logger.warning(f"Invalid config for org '{org_name}', skipping")
                continue

            org_rules[org_name] = _parse_rules(org_data.get("match", []))

            repos_data = org_data.get("repos", {})
            if repos_data:
                repo_rules[org_name] = {}
                for repo_name, repo_data in repos_data.items():
                    repo_rules[org_name][repo_name] = _parse_rules(repo_data)

        config = cls(
            default_rules=default_rules,
            org_rules=org_rules,
            repo_rules=repo_rules,
        )

        total = len(default_rules) + sum(len(r) for r in org_rules.values()) + sum(
            len(r) for repos in repo_rules.values() for r in repos.values()
        )
        logger.info(f"Loaded {total} rules from {path}")
        return config


def _parse_rules(items: list) -> list[Rule]:
    rules = []
    for item in items:
        if not isinstance(item, dict) or "reason" not in item:
            continue

        reason_str = item["reason"]
        reason = NotificationReason(reason_str)
        if reason == NotificationReason.UNKNOWN and reason_str != "unknown":
            logger.warning(f"Unknown reason '{reason_str}' in rules, skipping")
            continue

        action_str = item.get("action", "notify")
        try:
            action = Action(action_str)
        except ValueError:
            logger.warning(f"Unknown action '{action_str}' in rules, skipping")
            continue

        rules.append(Rule(reason=reason, action=action))
    return rules


_DEFAULT_RULES_TEMPLATE = """\
# octobell rules — controls which GitHub notifications fire and which are silently consumed.
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
# Evaluation order (first match wins):
#   1. rules.<org>.repos.<repo>  (most specific)
#   2. rules.<org>.match         (org-level)
#   3. default                   (global)
#   4. implicit notify           (if nothing matches)

# Global rules (apply to all orgs unless overridden)
default: []
  # - reason: ci_activity
  #   action: skip
  # - reason: subscribed
  #   action: skip

# Per-organization rules
# rules:
#   myorg:
#     match:
#       - reason: state_change
#         action: skip
#     repos:
#       noisy-repo:
#         - reason: comment
#           action: skip
"""


def _create_default_rules_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_DEFAULT_RULES_TEMPLATE)
    logger.info(f"Created default rules file at {path}")
