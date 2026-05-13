import logging
import signal
import threading

from octobell.browser import open_browser
from octobell.config import Config
from octobell.email_parser import EmailParser
from octobell.enums import NativeNotificationOutcome, NotificationReason
from octobell.imap_client import IMAPIdleClient
from octobell.models import GitHubEmail, NativeNotification
from octobell.notifier import get_notifier
from octobell.notifier.base import Notifier
from octobell.rules import Action, RulesConfig

logger = logging.getLogger(__name__)

REASON_TEXT = {
    NotificationReason.REVIEW_REQUESTED: "requested your review",
    NotificationReason.AUTHOR: "updated your pull request",
    NotificationReason.COMMENT: "commented",
    NotificationReason.MENTION: "mentioned you",
    NotificationReason.ASSIGN: "assigned you",
    NotificationReason.SUBSCRIBED: "updated",
    NotificationReason.TEAM_MENTION: "mentioned your team",
    NotificationReason.CI_ACTIVITY: "CI update",
    NotificationReason.STATE_CHANGE: "changed state",
}

_INTERESTING_EVENTS = (b"EXISTS", b"FETCH")


def _responses_contain_activity(responses: list) -> bool:
    for resp in responses:
        if isinstance(resp, (tuple, list)):
            for part in resp:
                if isinstance(part, bytes) and any(ev in part for ev in _INTERESTING_EVENTS):
                    return True
        elif isinstance(resp, bytes) and any(ev in resp for ev in _INTERESTING_EVENTS):
            return True
    return False


class FolderWatcher:
    def __init__(
        self,
        folder: str,
        config: Config,
        parser: EmailParser,
        notifier: Notifier,
        rules: RulesConfig,
        shutdown: threading.Event,
    ) -> None:
        self._folder = folder
        self._config = config
        self._imap = IMAPIdleClient(config)
        self._parser = parser
        self._notifier = notifier
        self._rules = rules
        self._shutdown = shutdown
        self._backoff_seconds = 1

    def run(self) -> None:
        logger.info(f"[{self._folder}] Watcher started")

        while not self._shutdown.is_set():
            try:
                self._imap.connect()
                self._imap.select_folder(self._folder)
                self._backoff_seconds = 1

                self._process_unseen()
                self._idle_loop()

            except Exception as e:
                logger.error(f"[{self._folder}] IMAP error: {e}", exc_info=True)
                self._imap.disconnect()

                if self._shutdown.is_set():
                    break

                logger.info(f"[{self._folder}] Reconnecting in {self._backoff_seconds}s...")
                self._shutdown.wait(timeout=self._backoff_seconds)
                self._backoff_seconds = min(
                    self._backoff_seconds * 2,
                    self._config.reconnect_max_backoff_seconds,
                )

        self._imap.disconnect()
        logger.info(f"[{self._folder}] Watcher stopped")

    def _idle_loop(self) -> None:
        poll_interval = 10

        while not self._shutdown.is_set():
            self._imap.idle_start()
            try:
                elapsed = 0
                all_responses = []

                while elapsed < self._config.idle_timeout_seconds:
                    if self._shutdown.is_set():
                        break
                    responses = self._imap.idle_check(timeout=poll_interval)
                    all_responses.extend(responses)
                    if responses:
                        break
                    elapsed += poll_interval
            finally:
                self._imap.idle_stop()

            if self._shutdown.is_set():
                break

            if all_responses:
                logger.debug(f"[{self._folder}] IDLE responses: {all_responses!r}")

            if _responses_contain_activity(all_responses):
                self._process_unseen()

    def _process_unseen(self) -> None:
        raw_emails = self._imap.fetch_unseen_github_emails()
        for uid, header_bytes, body_bytes in raw_emails:
            github_email = self._parser.parse(uid, header_bytes, body_bytes)
            if github_email is None:
                continue
            self._process_single(github_email)

    def _process_single(self, email: GitHubEmail) -> None:
        action = self._rules.evaluate(email)

        if action == Action.SKIP:
            logger.info(f"[{self._folder}] Skipped: {email.sender} {email.reason.value} on {email.repo_full_name}: {email.subject_title}")
            self._imap.mark_seen(email.uid)
            return

        logger.info(f"[{self._folder}] {email.sender} {email.reason.value} on {email.repo_full_name}: {email.subject_title}")

        notification = NativeNotification(
            title="GitHub",
            subtitle=self._build_subtitle(email),
            message=email.subject_title,
            on_trigger_url=email.web_url,
        )

        outcome = self._notifier.notify(notification)

        if outcome == NativeNotificationOutcome.OPEN_URL:
            open_browser(email.web_url)

        self._imap.mark_seen(email.uid)

    def _build_subtitle(self, email: GitHubEmail) -> str:
        action = REASON_TEXT.get(email.reason, "notification")
        return f"{email.sender} {action} on {email.repo_full_name}"


class Daemon:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._parser = EmailParser()
        self._notifier: Notifier = get_notifier()
        self._rules = RulesConfig.load(config.rules_path)
        self._shutdown = threading.Event()

    def run(self) -> None:
        self._install_signal_handlers()
        folders = self._config.imap_folders
        logger.info(f"Starting octobell (notifier: {type(self._notifier).__name__}, folders: {', '.join(folders)})")

        watchers = []
        threads = []

        for folder in folders:
            watcher = FolderWatcher(
                folder=folder,
                config=self._config,
                parser=self._parser,
                notifier=self._notifier,
                rules=self._rules,
                shutdown=self._shutdown,
            )
            watchers.append(watcher)
            thread = threading.Thread(
                target=watcher.run,
                name=f"watcher-{folder}",
                daemon=True,
            )
            threads.append(thread)
            thread.start()

        self._shutdown.wait()

        for thread in threads:
            thread.join(timeout=15)

        logger.info("Daemon stopped")

    def _install_signal_handlers(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_signal)

    def _handle_signal(self, signum, frame) -> None:
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown.set()
