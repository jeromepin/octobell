from dataclasses import dataclass

from octobell.enums import NativeNotificationOutcome
from octobell.models import NativeNotification
from octobell.notifier.base import Notifier


@dataclass
class ConsoleNotifier(Notifier):
    @property
    def is_available(self) -> bool:
        return True

    def notify(self, notification: NativeNotification) -> NativeNotificationOutcome:
        print(f"[Notification] {notification.title}: {notification.subtitle}")
        return NativeNotificationOutcome.DO_NOTHING
