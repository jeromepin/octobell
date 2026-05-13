import email
import logging
import re
from email.header import decode_header
from email.message import Message

from octobell.enums import NotificationReason, event_type_from_action_text
from octobell.models import GitHubEmail

logger = logging.getLogger(__name__)

_SUBJECT_PATTERN = re.compile(
    r"^(?:Re:\s*)?\[(?P<repo>[^\]]+)\]\s+(?P<title>.+?)(?:\s+\((?:PR )?#(?P<number>\d+)\))?\s*$"
)

_LIST_ID_PATTERN = re.compile(
    r"<(?P<repo>[^.]+)\.(?P<owner>[^.]+)\.github\.com>"
)

_GITHUB_URL_PATTERN = re.compile(
    r"https://github\.com/[^\s\]>)\"']+"
)

_ACTION_PATTERN = re.compile(
    r"^@?\S+\s+(.+?)\s*(?:\([\w/]+#\d+\))?\s*[.:]?\s*$"
)


class EmailParser:
    def parse(self, uid: int, header_bytes: bytes, body_bytes: bytes = b"") -> GitHubEmail | None:
        msg: Message = email.message_from_bytes(header_bytes)

        from_addr = msg.get("From", "")
        if "notifications@github.com" not in from_addr:
            return None

        reason_raw = msg.get("X-GitHub-Reason", "unknown")
        sender = msg.get("X-GitHub-Sender", "unknown")
        list_id = msg.get("List-ID", "")
        message_id = msg.get("Message-ID", "")
        subject = self._decode_subject(msg.get("Subject", ""))

        logger.debug(f"Parsing email: List-ID={list_id!r} Subject={subject!r} Reason={reason_raw} Sender={sender}")
        repo_owner, repo_name = self._parse_list_id(list_id)
        subject_title, issue_number = self._parse_subject(subject)

        web_url = self._extract_url_from_body(body_bytes)
        if not web_url:
            web_url = f"https://github.com/{repo_owner}/{repo_name}"
            if issue_number is not None:
                web_url += f"/pull/{issue_number}"

        action_text = self._extract_action_from_body(body_bytes)
        body_str = body_bytes.decode("utf-8", errors="replace") if body_bytes else None
        event_type = event_type_from_action_text(action_text, body_str)

        return GitHubEmail(
            uid=uid,
            message_id=message_id,
            reason=NotificationReason(reason_raw),
            sender=sender,
            repo_owner=repo_owner,
            repo_name=repo_name,
            subject_title=subject_title,
            issue_number=issue_number,
            web_url=web_url,
            action_text=action_text,
            event_type=event_type,
        )

    def _decode_subject(self, raw_subject: str) -> str:
        unfolded = re.sub(r"\r?\n\s+", " ", raw_subject)
        decoded_parts = decode_header(unfolded)
        return "".join(
            part.decode(charset or "utf-8") if isinstance(part, bytes) else part
            for part, charset in decoded_parts
        )

    def _parse_list_id(self, list_id: str) -> tuple[str, str]:
        match = _LIST_ID_PATTERN.search(list_id)
        if match:
            return match.group("owner"), match.group("repo")
        return "unknown", "unknown"

    def _extract_url_from_body(self, body_bytes: bytes) -> str | None:
        if not body_bytes:
            return None
        try:
            body = body_bytes.decode("utf-8", errors="replace")
        except Exception:
            return None
        urls = _GITHUB_URL_PATTERN.findall(body)
        if not urls:
            return None
        # Last URL is typically the "View it on GitHub" link
        return urls[-1]

    def _extract_action_from_body(self, body_bytes: bytes) -> str | None:
        if not body_bytes:
            return None
        try:
            body = body_bytes.decode("utf-8", errors="replace")
        except Exception:
            return None
        first_line = body.strip().split("\n", 1)[0].strip()
        match = _ACTION_PATTERN.match(first_line)
        if match:
            return match.group(1)
        return None

    def _parse_subject(self, subject: str) -> tuple[str, int | None]:
        match = _SUBJECT_PATTERN.match(subject)
        if match:
            title = match.group("title")
            num_str = match.group("number")
            return title, int(num_str) if num_str else None
        return subject, None
