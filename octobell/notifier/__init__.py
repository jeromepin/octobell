import logging

from octobell.enums import Platform, get_platform
from octobell.notifier.alerter import AlerterNotifier
from octobell.notifier.base import Notifier
from octobell.notifier.console import ConsoleNotifier
from octobell.notifier.notify_send import NotifySendNotifier

logger = logging.getLogger(__name__)


def get_notifier() -> Notifier:
    system = get_platform()

    if system == Platform.DARWIN:
        alerter = AlerterNotifier()
        if alerter.is_available:
            return alerter
        logger.warning("alerter not found on macOS. Falling back to console.")

    elif system == Platform.LINUX:
        notifier = NotifySendNotifier()
        if notifier.is_available:
            return notifier
        logger.warning("notify-send not found on Linux. Falling back to console.")

    return ConsoleNotifier()
