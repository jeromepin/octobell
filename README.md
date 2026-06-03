# octobell

Native desktop notifications for GitHub, powered by your email inbox.

octobell connects to your email account(s) via IMAP, watches for GitHub notification emails in near-realtime using IMAP IDLE, and fires native macOS or Linux notifications. Click a notification to open the relevant PR or comment in your browser.

## How it works

1. GitHub sends notification emails to your inbox (this is the default behavior)
2. octobell connects to your email via IMAP and enters IDLE mode
3. When a new GitHub email arrives, octobell parses its headers and body
4. A native desktop notification is displayed
5. The email is marked as read


## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended)
- **macOS**: [alerter](https://github.com/vjeantet/alerter) for native notifications
- **Linux**: `notify-send` (from `libnotify-bin`)

### Installing alerter (macOS)

```bash
brew install vjeantet/tap/alerter
```

Without alerter, octobell falls back to printing notifications to the console.

## Installation

```bash
git clone https://github.com/jeromepin/octobell.git
cd octobell
uv sync
```

## Usage

```bash
uv run octobell
```

Set log level with the `OCTOBELL_LOG_LEVEL` environment variable (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default is `INFO`.

octobell will:
- Connect to all configured IMAP accounts
- Process any existing unread GitHub emails
- Enter IDLE mode and wait for new emails
- Display a native notification for each GitHub email
- Mark the email as read after notification

Press `Ctrl-C` to stop.

## Configuration

See the [configuration guide](docs/configuration.md). On first run, a template config file is created at `~/.config/octobell/default.yml`.

### Rules

Rules let you control which notifications fire and which are silently consumed. See the [rules documentation](docs/rules.md) for details on available reasons, events, evaluation order, and examples.

### What you see

Each notification shows:
- **Title**: "GitHub"
- **Subtitle**: who did what (e.g., "alice requested your review on myorg/myrepo")
- **Message**: the PR or issue title

Clicking a notification opens the relevant GitHub page in your browser (the exact comment or review, not just the PR).


## Troubleshooting

See the [troubleshooting guide](docs/troubleshooting.md).

## Architecture

```
~/.config/octobell/*.yml
    |
    v
load_accounts() → list[AccountConfig]
    |
    v
Daemon (one per process)
    |
    ├─ AccountConfig "personal" / INBOX  → FolderWatcher thread
    ├─ AccountConfig "work" / INBOX      → FolderWatcher thread
    └─ AccountConfig "work" / GitHub     → FolderWatcher thread

Each FolderWatcher:
    IMAP Server
        |
        v
    IMAPIdleClient -- IDLE --> new mail?
        |                        |
        |<-----------------------+
        v
    EmailParser.parse(headers + body) --> GitHubEmail
        |
        v
    RulesConfig.evaluate(email) --> notify or skip?
        |
        v
    Notifier.notify() --> native notification
        |
        v
    mark email as read
```
