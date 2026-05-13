import platform
from enum import Enum, auto, unique


@unique
class NotificationReason(str, Enum):
    ASSIGN = "assign"
    AUTHOR = "author"
    COMMENT = "comment"
    INVITATION = "invitation"
    MANUAL = "manual"
    MENTION = "mention"
    REVIEW_REQUESTED = "review_requested"
    SECURITY_ALERT = "security_alert"
    STATE_CHANGE = "state_change"
    SUBSCRIBED = "subscribed"
    TEAM_MENTION = "team_mention"
    CI_ACTIVITY = "ci_activity"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


@unique
class EventType(str, Enum):
    COMMENT = "comment"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    MERGED = "merged"
    CLOSED = "closed"
    REOPENED = "reopened"
    PUSH = "push"
    REVIEW_DISMISSED = "review_dismissed"
    PR_OPENED = "pr_opened"
    REVIEW_REQUESTED = "review_requested"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


_ACTION_TEXT_TO_EVENT = {
    "left a comment": EventType.COMMENT,
    "approved this pull request": EventType.APPROVED,
    "requested changes on this pull request": EventType.CHANGES_REQUESTED,
    "merged this pull request": EventType.MERGED,
    "closed this": EventType.CLOSED,
    "reopened this": EventType.REOPENED,
    "pushed": EventType.PUSH,
    "dismissed": EventType.REVIEW_DISMISSED,
    "requested your review": EventType.REVIEW_REQUESTED,
}

_BODY_PATTERN_TO_EVENT = {
    "you can view, comment on, or merge this pull request": EventType.PR_OPENED,
}


def event_type_from_action_text(action_text: str | None, body: str | None = None) -> EventType | None:
    if action_text:
        lower = action_text.lower()
        for keyword, event in _ACTION_TEXT_TO_EVENT.items():
            if keyword in lower:
                return event

    if body:
        lower_body = body.strip().lower()
        for pattern, event in _BODY_PATTERN_TO_EVENT.items():
            if lower_body.startswith(pattern):
                return event

    if action_text is not None:
        return EventType.UNKNOWN

    return None


class NativeNotificationOutcome(Enum):
    OPEN_URL = auto()
    DISMISS = auto()
    ERROR = auto()
    DO_NOTHING = auto()


class Platform(Enum):
    DARWIN = auto()
    LINUX = auto()
    UNKNOWN = auto()


def get_platform() -> Platform:
    system = platform.system()
    if system == "Darwin":
        return Platform.DARWIN
    elif system == "Linux":
        return Platform.LINUX
    return Platform.UNKNOWN
