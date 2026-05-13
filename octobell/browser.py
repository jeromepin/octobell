import logging
import platform
import subprocess

logger = logging.getLogger(__name__)

BROWSER_APP = "Brave Browser.app"


def open_browser(url: str) -> None:
    if not url:
        return

    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", "-a", BROWSER_APP, url], check=True)
        else:
            import webbrowser
            webbrowser.open(url)
    except subprocess.CalledProcessError:
        import webbrowser
        webbrowser.open(url)
