from octobell.email_parser import EmailParser
from octobell.enums import EventType, NotificationReason


def _make_headers(
    sender="alice",
    reason="comment",
    list_id="<repo.owner.github.com>",
    subject="[owner/repo] Fix the bug (#42)",
    from_addr="Alice <notifications@github.com>",
    message_id="<abc@github.com>",
):
    lines = [
        f"From: {from_addr}",
        f"Subject: {subject}",
        f"X-GitHub-Reason: {reason}",
        f"X-GitHub-Sender: {sender}",
        f"List-ID: {list_id}",
        f"Message-ID: {message_id}",
    ]
    return "\r\n".join(lines).encode()


class TestEmailParser:
    def setup_method(self):
        self.parser = EmailParser()

    def test_basic_parse(self):
        headers = _make_headers()
        result = self.parser.parse(1, headers)
        assert result is not None
        assert result.uid == 1
        assert result.sender == "alice"
        assert result.reason == NotificationReason.COMMENT
        assert result.repo_owner == "owner"
        assert result.repo_name == "repo"
        assert result.subject_title == "Fix the bug"
        assert result.issue_number == 42

    def test_non_github_email_returns_none(self):
        headers = _make_headers(from_addr="someone@example.com")
        assert self.parser.parse(1, headers) is None

    def test_repo_full_name(self):
        result = self.parser.parse(1, _make_headers())
        assert result is not None
        assert result.repo_full_name == "owner/repo"

    def test_unknown_reason(self):
        result = self.parser.parse(1, _make_headers(reason="nonexistent"))
        assert result is not None
        assert result.reason == NotificationReason.UNKNOWN

    def test_body_extracts_action_text(self):
        body = b"@alice left a comment on this pull request."
        result = self.parser.parse(1, _make_headers(), body)
        assert result is not None
        assert result.action_text == "left a comment on this pull request"
        assert result.event_type == EventType.COMMENT

    def test_body_extracts_url(self):
        body = b"View it on GitHub:\nhttps://github.com/owner/repo/pull/42#comment-123"
        result = self.parser.parse(1, _make_headers(), body)
        assert result is not None
        assert result.web_url == "https://github.com/owner/repo/pull/42#comment-123"

    def test_no_body_builds_url_from_metadata(self):
        result = self.parser.parse(1, _make_headers())
        assert result is not None
        assert "github.com/owner/repo" in result.web_url

    def test_subject_without_issue_number(self):
        headers = _make_headers(subject="[owner/repo] Add feature")
        result = self.parser.parse(1, headers)
        assert result is not None
        assert result.subject_title == "Add feature"
        assert result.issue_number is None

    def test_subject_with_pr_prefix(self):
        headers = _make_headers(subject="[owner/repo] Refactor (PR #99)")
        result = self.parser.parse(1, headers)
        assert result is not None
        assert result.subject_title == "Refactor"
        assert result.issue_number == 99

    def test_re_prefix_stripped(self):
        headers = _make_headers(subject="Re: [owner/repo] Fix bug (#10)")
        result = self.parser.parse(1, headers)
        assert result is not None
        assert result.subject_title == "Fix bug"
        assert result.issue_number == 10
