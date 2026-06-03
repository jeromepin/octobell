from octobell.enums import EventType, NotificationReason
from octobell.models import GitHubEmail
from octobell.rules import Action, Rule, RulesConfig, _parse_rules


def _email(
    reason=NotificationReason.COMMENT,
    event_type=None,
    repo_owner="org",
    repo_name="repo",
):
    return GitHubEmail(
        uid=1,
        message_id="<test@github.com>",
        reason=reason,
        sender="alice",
        repo_owner=repo_owner,
        repo_name=repo_name,
        subject_title="Fix bug",
        issue_number=42,
        web_url="https://github.com/org/repo/pull/42",
        event_type=event_type,
    )


class TestParseRules:
    def test_empty(self):
        assert _parse_rules([]) == []

    def test_basic_rule(self):
        rules = _parse_rules([{"reason": "comment", "action": "skip"}])
        assert len(rules) == 1
        assert rules[0].reason == NotificationReason.COMMENT
        assert rules[0].action == Action.SKIP
        assert rules[0].event is None

    def test_rule_with_event(self):
        rules = _parse_rules([{"reason": "review_requested", "action": "notify", "event": "approved"}])
        assert rules[0].event == EventType.APPROVED

    def test_default_action_is_notify(self):
        rules = _parse_rules([{"reason": "mention"}])
        assert rules[0].action == Action.NOTIFY


class TestRulesConfigFromDict:
    def test_empty(self):
        cfg = RulesConfig.from_dict({})
        assert cfg.default_rules == []
        assert cfg.org_rules == {}
        assert cfg.repo_rules == {}

    def test_default_rules(self):
        cfg = RulesConfig.from_dict({"default": [{"reason": "ci_activity", "action": "skip"}]})
        assert len(cfg.default_rules) == 1

    def test_org_rules(self):
        cfg = RulesConfig.from_dict(
            {
                "orgs": {"myorg": {"match": [{"reason": "comment", "action": "skip"}]}},
            }
        )
        assert len(cfg.org_rules["myorg"]) == 1

    def test_repo_rules(self):
        cfg = RulesConfig.from_dict(
            {
                "orgs": {
                    "myorg": {
                        "repos": {"myrepo": [{"reason": "mention", "action": "skip"}]},
                    },
                },
            }
        )
        assert len(cfg.repo_rules["myorg"]["myrepo"]) == 1


class TestRulesEvaluation:
    def test_no_rules_defaults_to_notify(self):
        cfg = RulesConfig.empty()
        assert cfg.evaluate(_email()) == Action.NOTIFY

    def test_default_rule_matches(self):
        cfg = RulesConfig(default_rules=[Rule(NotificationReason.COMMENT, Action.SKIP)])
        assert cfg.evaluate(_email(reason=NotificationReason.COMMENT)) == Action.SKIP

    def test_default_rule_no_match(self):
        cfg = RulesConfig(default_rules=[Rule(NotificationReason.CI_ACTIVITY, Action.SKIP)])
        assert cfg.evaluate(_email(reason=NotificationReason.COMMENT)) == Action.NOTIFY

    def test_org_rule_takes_precedence_over_default(self):
        cfg = RulesConfig(
            default_rules=[Rule(NotificationReason.COMMENT, Action.NOTIFY)],
            org_rules={"org": [Rule(NotificationReason.COMMENT, Action.SKIP)]},
        )
        assert cfg.evaluate(_email(reason=NotificationReason.COMMENT)) == Action.SKIP

    def test_repo_rule_takes_precedence_over_org(self):
        cfg = RulesConfig(
            org_rules={"org": [Rule(NotificationReason.COMMENT, Action.NOTIFY)]},
            repo_rules={"org": {"repo": [Rule(NotificationReason.COMMENT, Action.SKIP)]}},
        )
        assert cfg.evaluate(_email(reason=NotificationReason.COMMENT)) == Action.SKIP

    def test_event_filter(self):
        cfg = RulesConfig(
            default_rules=[Rule(NotificationReason.COMMENT, Action.SKIP, event=EventType.APPROVED)],
        )
        assert cfg.evaluate(_email(reason=NotificationReason.COMMENT, event_type=EventType.APPROVED)) == Action.SKIP
        assert cfg.evaluate(_email(reason=NotificationReason.COMMENT, event_type=EventType.MERGED)) == Action.NOTIFY

    def test_first_match_wins(self):
        cfg = RulesConfig(
            default_rules=[
                Rule(NotificationReason.COMMENT, Action.SKIP),
                Rule(NotificationReason.COMMENT, Action.NOTIFY),
            ],
        )
        assert cfg.evaluate(_email(reason=NotificationReason.COMMENT)) == Action.SKIP
