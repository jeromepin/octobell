from dataclasses import dataclass, field
from enum import StrEnum, unique

from octobell.enums import EventType, NotificationReason
from octobell.models import GitHubEmail


@unique
class Action(StrEnum):
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

        default_rules = _parse_rules(data.get("default", []))

        org_rules: dict[str, list[Rule]] = {}
        repo_rules: dict[str, dict[str, list[Rule]]] = {}

        for org_name, org_data in data.get("orgs", {}).items():
            org_rules[org_name] = _parse_rules(org_data.get("match", []))

            repos_data = org_data.get("repos", {})
            if repos_data:
                repo_rules[org_name] = {
                    repo_name: _parse_rules(repo_data) for repo_name, repo_data in repos_data.items()
                }

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
    return [
        Rule(
            reason=NotificationReason(item["reason"]),
            action=Action(item.get("action", "notify")),
            event=EventType(item["event"]) if "event" in item else None,
        )
        for item in items
    ]
