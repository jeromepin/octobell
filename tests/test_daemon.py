from octobell.config import AccountConfig
from octobell.daemon import REASON_TEXT, FolderWatcher, _responses_contain_activity
from octobell.enums import NotificationReason
from octobell.models import GitHubEmail


def _email(
    sender="alice",
    reason=NotificationReason.COMMENT,
    action_text=None,
    repo_owner="org",
    repo_name="repo",
    subject_title="Fix bug",
):
    return GitHubEmail(
        uid=1,
        message_id="<test@github.com>",
        reason=reason,
        sender=sender,
        repo_owner=repo_owner,
        repo_name=repo_name,
        subject_title=subject_title,
        issue_number=42,
        web_url="https://github.com/org/repo/pull/42",
        action_text=action_text,
    )


def _account(**overrides: str) -> AccountConfig:
    return AccountConfig(
        name=overrides.get("name", "test"),
        imap_host=overrides.get("imap_host", "imap.example.com"),
        imap_user=overrides.get("imap_user", "u@example.com"),
        imap_password=overrides.get("imap_password", "secret"),
        notification_subtitle_format=overrides.get("notification_subtitle_format", "{sender} {action} on {repo}"),
        notification_message_format=overrides.get("notification_message_format", "{title}"),
    )


class TestResponsesContainActivity:
    def test_exists_event(self):
        assert _responses_contain_activity([b"1 EXISTS"]) is True

    def test_fetch_event(self):
        assert _responses_contain_activity([b"1 FETCH (FLAGS (\\Seen))"]) is True

    def test_no_activity(self):
        assert _responses_contain_activity([b"OK"]) is False

    def test_empty(self):
        assert _responses_contain_activity([]) is False

    def test_nested_tuple(self):
        assert _responses_contain_activity([(b"1 EXISTS",)]) is True


class TestTemplateVars:
    def _build_watcher(self, **account_overrides):
        import threading

        from octobell.email_parser import EmailParser
        from octobell.notifier.console import ConsoleNotifier

        return FolderWatcher(
            folder="INBOX",
            account=_account(**account_overrides),
            parser=EmailParser(),
            notifier=ConsoleNotifier(),
            shutdown=threading.Event(),
        )

    def test_default_subtitle_format(self):
        watcher = self._build_watcher()
        email = _email(action_text="left a comment")
        v = watcher._template_vars(email)
        result = watcher._account.notification_subtitle_format.format_map(v)
        assert result == "alice left a comment on org/repo"

    def test_reason_fallback_when_no_action_text(self):
        watcher = self._build_watcher()
        email = _email(reason=NotificationReason.REVIEW_REQUESTED)
        v = watcher._template_vars(email)
        assert v["action"] == REASON_TEXT[NotificationReason.REVIEW_REQUESTED]

    def test_custom_subtitle_format(self):
        watcher = self._build_watcher(notification_subtitle_format="[{repo}] {sender}: {action}")
        email = _email(action_text="commented")
        v = watcher._template_vars(email)
        result = watcher._account.notification_subtitle_format.format_map(v)
        assert result == "[org/repo] alice: commented"

    def test_custom_message_format(self):
        watcher = self._build_watcher(notification_message_format="{title} on {repo}")
        email = _email(subject_title="Fix bug")
        v = watcher._template_vars(email)
        result = watcher._account.notification_message_format.format_map(v)
        assert result == "Fix bug on org/repo"

    def test_template_vars_keys(self):
        watcher = self._build_watcher()
        v = watcher._template_vars(_email())
        assert set(v.keys()) == {"sender", "action", "repo", "repo_owner", "repo_name", "reason", "title"}
