import logging

import imapclient

from octobell.config import Config

logger = logging.getLogger(__name__)


class IMAPIdleClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client: imapclient.IMAPClient | None = None

    def connect(self) -> None:
        self._client = imapclient.IMAPClient(
            self._config.imap_host,
            port=self._config.imap_port,
            ssl=True,
            timeout=30,
        )
        self._client.login(self._config.imap_user, self._config.imap_password)
        logger.info(f"Connected to {self._config.imap_host} as {self._config.imap_user}")

    def select_folder(self, folder: str) -> dict:
        info = self._client.select_folder(folder)
        logger.info(f"Selected folder {folder} ({info.get(b'EXISTS', 0)} messages)")
        return info

    def fetch_unseen_github_emails(self) -> list[tuple[int, bytes, bytes]]:
        uids = self._client.search(["UNSEEN", "FROM", "notifications@github.com"])
        logger.debug(f"SEARCH UNSEEN FROM notifications@github.com → {len(uids)} UIDs")
        if not uids:
            return []

        logger.info(f"Found {len(uids)} unseen GitHub emails")
        fetched = self._client.fetch(uids, ["BODY.PEEK[HEADER]", "BODY.PEEK[1]"])

        results = []
        for uid, data in fetched.items():
            header_bytes = data.get(b"BODY[HEADER]", b"")
            body_bytes = data.get(b"BODY[1]", b"")
            results.append((uid, header_bytes, body_bytes))
        return results

    def mark_seen(self, uid: int) -> None:
        self._client.set_flags([uid], [imapclient.SEEN])
        logger.debug(f"Marked UID {uid} as seen")

    def idle_start(self) -> None:
        self._client.idle()
        logger.debug("IDLE started")

    def idle_check(self, timeout: int | None = None) -> list:
        timeout = timeout or self._config.idle_timeout_seconds
        return self._client.idle_check(timeout=timeout)

    def idle_stop(self) -> bytes:
        result = self._client.idle_done()
        logger.debug("IDLE stopped")
        return result

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None
            logger.info("Disconnected")

    def reconnect(self, folder: str) -> None:
        self.disconnect()
        self.connect()
        self.select_folder(folder)
