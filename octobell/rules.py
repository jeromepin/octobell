import logging
from dataclasses import dataclass, field
from enum import Enum, unique

from octobell.enums import EventType, NotificationReason
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
    event: EventType | None = None


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
                if _rule_matches(rule, email):
                    return rule.action

        if org in self.org_rules:
            for rule in self.org_rules[org]:
                if _rule_matches(rule, email):
                    return rule.action

        for rule in self.default_rules:
            if _rule_matches(rule, email):
                return rule.action

        return Action.NOTIFY

    @classmethod
    def empty(cls) -> "RulesConfig":
        return cls()

    @classmethod
    def from_dict(cls, data: dict) -> "RulesConfig":
        if not data:
            return cls.empty()

        unknown_keys = set(data.keys()) - {"default", "orgs"}
        if unknown_keys:
            logger.warning(f"Unknown key(s) in 'rules': {', '.join(sorted(unknown_keys))}")

        default_data = data.get("default", [])
        if default_data and not isinstance(default_data, list):
            logger.warning(f"'rules.default' must be a list, got {type(default_data).__name__}; ignoring")
            default_data = []
        default_rules = _parse_rules(default_data)

        orgs_data = data.get("orgs", {})
        if orgs_data and not isinstance(orgs_data, dict):
            logger.warning(f"'rules.orgs' must be a mapping, got {type(orgs_data).__name__}; ignoring")
            orgs_data = {}

        org_rules: dict[str, list[Rule]] = {}
        repo_rules: dict[str, dict[str, list[Rule]]] = {}

        for org_name, org_data in orgs_data.items():
            if not isinstance(org_data, dict):
                logger.warning(f"'rules.orgs.{org_name}' must be a mapping, got {type(org_data).__name__}; skipping")
                continue

            unknown_org_keys = set(org_data.keys()) - {"match", "repos"}
            if unknown_org_keys:
                logger.warning(f"Unknown key(s) in 'rules.orgs.{org_name}': {', '.join(sorted(unknown_org_keys))}")

            org_rules[org_name] = _parse_rules(org_data.get("match", []))

            repos_data = org_data.get("repos", {})
            if repos_data:
                if not isinstance(repos_data, dict):
                    logger.warning(f"'rules.orgs.{org_name}.repos' must be a mapping; skipping")
                    continue
                repo_rules[org_name] = {}
                for repo_name, repo_data in repos_data.items():
                    if not isinstance(repo_data, list):
                        logger.warning(f"'rules.orgs.{org_name}.repos.{repo_name}' must be a list; skipping")
                        continue
                    repo_rules[org_name][repo_name] = _parse_rules(repo_data)

        return cls(
            default_rules=default_rules,
            org_rules=org_rules,
            repo_rules=repo_rules,
        )


def _rule_matches(rule: Rule, email: GitHubEmail) -> bool:
    if rule.reason != email.reason:
        return False
    if rule.event is None:
        return True
    return email.event_type == rule.event


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

        event = None
        event_str = item.get("event")
        if event_str:
            event = EventType(event_str)
            if event == EventType.UNKNOWN and event_str != "unknown":
                logger.warning(f"Unknown event '{event_str}' in rules, skipping")
                continue

        rules.append(Rule(reason=reason, action=action, event=event))
    return rules
