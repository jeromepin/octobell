import logging
import webbrowser

logger = logging.getLogger(__name__)


def open_browser(url: str) -> None:
    if not url:
        return

    try:
        webbrowser.open(url)
    except Exception:
        logger.warning(f"Failed to open browser for {url}")
