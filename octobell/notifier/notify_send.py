import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Final

from octobell.enums import NativeNotificationOutcome
from octobell.models import NativeNotification
from octobell.notifier.base import Notifier

logger = logging.getLogger(__name__)


@dataclass
class NotifySendNotifier(Notifier):
    CMD: Final[str] = "notify-send"

    @property
    def is_available(self) -> bool:
        return shutil.which(self.CMD) is not None

    def notify(self, notification: NativeNotification) -> NativeNotificationOutcome:
        args = [
            self.CMD,
            notification.subtitle,
            notification.message,
        ]

        subprocess.run(args, capture_output=True, text=True, check=False)
        return NativeNotificationOutcome.DO_NOTHING
