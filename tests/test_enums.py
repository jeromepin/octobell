from octobell.enums import (
    EventType,
    NotificationReason,
    Platform,
    event_type_from_action_text,
    get_platform,
)


class TestNotificationReason:
    def test_known_value(self):
        assert NotificationReason("comment") == NotificationReason.COMMENT

    def test_unknown_value_falls_back(self):
        assert NotificationReason("nonexistent") == NotificationReason.UNKNOWN

    def test_all_values_are_strings(self):
        for member in NotificationReason:
            assert isinstance(member.value, str)


class TestEventType:
    def test_known_value(self):
        assert EventType("merged") == EventType.MERGED

    def test_unknown_value_falls_back(self):
        assert EventType("nonexistent") == EventType.UNKNOWN


class TestEventTypeFromActionText:
    def test_left_a_comment(self):
        assert event_type_from_action_text("left a comment") == EventType.COMMENT

    def test_approved(self):
        assert event_type_from_action_text("approved this pull request") == EventType.APPROVED

    def test_merged(self):
        assert event_type_from_action_text("merged this pull request") == EventType.MERGED

    def test_case_insensitive(self):
        assert event_type_from_action_text("Left A Comment") == EventType.COMMENT

    def test_unknown_action_text(self):
        assert event_type_from_action_text("did something weird") == EventType.UNKNOWN

    def test_none_action_text_no_body(self):
        assert event_type_from_action_text(None) is None

    def test_none_action_text_with_pr_body(self):
        body = "You can view, comment on, or merge this pull request online"
        assert event_type_from_action_text(None, body) == EventType.PR_OPENED

    def test_none_action_text_with_unmatched_body(self):
        assert event_type_from_action_text(None, "some other body") is None


class TestGetPlatform:
    def test_returns_platform_enum(self):
        result = get_platform()
        assert isinstance(result, Platform)
