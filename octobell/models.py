from dataclasses import dataclass

from octobell.enums import EventType, NotificationReason


@dataclass(frozen=True)
class GitHubEmail:
    uid: int
    message_id: str
    reason: NotificationReason
    sender: str
    repo_owner: str
    repo_name: str
    subject_title: str
    issue_number: int | None
    web_url: str
    action_text: str | None = None
    event_type: EventType | None = None

    @property
    def repo_full_name(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"


@dataclass
class NativeNotification:
    subtitle: str
    message: str
    on_trigger_url: str
    title: str = "GitHub"
    on_dismiss: str | None = None
