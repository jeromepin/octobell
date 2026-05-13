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
