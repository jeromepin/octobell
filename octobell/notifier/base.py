from abc import ABC, abstractmethod
from dataclasses import dataclass

from octobell.enums import NativeNotificationOutcome
from octobell.models import NativeNotification


@dataclass
class Notifier(ABC):
    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def notify(self, notification: NativeNotification) -> NativeNotificationOutcome: ...
