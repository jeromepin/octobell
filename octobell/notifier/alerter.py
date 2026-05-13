import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Final

from octobell.enums import NativeNotificationOutcome
from octobell.models import NativeNotification
from octobell.notifier.base import Notifier

logger = logging.getLogger(__name__)

CLOSE_LABEL: Final[str] = "Dismiss"
TIMEOUT_SECONDS: Final[int] = 10


@dataclass
class AlerterNotifier(Notifier):
    CMD: Final[str] = "alerter"

    @property
    def is_available(self) -> bool:
        return shutil.which(self.CMD) is not None

    def notify(self, notification: NativeNotification) -> NativeNotificationOutcome:
        args = [
            self.CMD,
            "--title", notification.title,
            "--subtitle", notification.subtitle,
            "--message", notification.message,
            "--close-label", CLOSE_LABEL,
            "--timeout", str(TIMEOUT_SECONDS),
            "--json",
        ]

        logger.debug(f"Running: {' '.join(args)}")
        process = subprocess.run(args, capture_output=True, text=True, check=False)
        logger.debug(f"alerter exit={process.returncode} stdout={process.stdout!r} stderr={process.stderr!r}")

        try:
            result = json.loads(process.stdout.strip())
        except (json.JSONDecodeError, ValueError):
            logger.error(f"Failed to parse alerter output: exit={process.returncode} stdout={process.stdout!r} stderr={process.stderr!r}")
            return NativeNotificationOutcome.ERROR

        if (
            result.get("activationType") == "closed"
            and result.get("activationValue") == CLOSE_LABEL
        ):
            return NativeNotificationOutcome.DISMISS
        elif result.get("activationType") == "contentsClicked":
            return NativeNotificationOutcome.OPEN_URL

        return NativeNotificationOutcome.DISMISS
