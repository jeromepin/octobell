# octobell

Native desktop notifications for GitHub, powered by your email inbox.

octobell connects to your email account via IMAP, watches for GitHub notification emails in near-realtime using IMAP IDLE, and fires native macOS or Linux notifications. Click a notification to open the relevant PR or comment in your browser.

## How it works

1. GitHub sends notification emails to your inbox (this is the default behavior)
2. octobell connects to your email via IMAP and enters IDLE mode
3. When a new GitHub email arrives, octobell parses its headers and body
4. A native desktop notification is displayed
5. The email is marked as read

No GitHub API token needed. No polling. Works with any email provider that supports IMAP.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
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

## Configuration

### Email credentials

Set the following environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OCTOBELL_IMAP_HOST` | yes | | IMAP server hostname |
| `OCTOBELL_IMAP_PORT` | no | `993` | IMAP server port (TLS) |
| `OCTOBELL_IMAP_USER` | yes | | Email address / username |
| `OCTOBELL_IMAP_PASSWORD` | yes | | Email password or app password |
| `OCTOBELL_IMAP_FOLDERS` | no | `INBOX` | Comma-separated IMAP folders to watch |
| `OCTOBELL_RULES_PATH` | no | `~/.config/octobell/rules.yml` | Path to rules file |
| `OCTOBELL_LOG_LEVEL` | no | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Gmail setup

1. Enable 2-Step Verification on your Google account
2. Go to [App passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Enable IMAP in Gmail: Settings > Forwarding and POP/IMAP > Enable IMAP

```bash
export OCTOBELL_IMAP_HOST=imap.gmail.com
export OCTOBELL_IMAP_USER=you@gmail.com
export OCTOBELL_IMAP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # the app password
```

### Other providers

Any IMAP provider works. Use your provider's IMAP hostname and port. Examples:

| Provider | Host | Port |
|----------|------|------|
| Gmail | `imap.gmail.com` | 993 |
| Outlook | `outlook.office365.com` | 993 |
| Fastmail | `imap.fastmail.com` | 993 |
| ProtonMail (Bridge) | `127.0.0.1` | 1143 |

### Watching specific folders

If you have a Gmail filter that routes GitHub emails to a label (e.g., "GitHub"), set:

```bash
export OCTOBELL_IMAP_FOLDERS=GitHub
```

You can watch multiple folders simultaneously (each gets its own IMAP connection):

```bash
export OCTOBELL_IMAP_FOLDERS=INBOX,GitHub
```

Note: Gmail IMAP IDLE may not send push notifications for emails arriving in labels other than INBOX. If notifications are delayed, use `INBOX` instead.

## Usage

```bash
uv run python -m octobell
```

octobell will:
- Connect to your IMAP server
- Process any existing unread GitHub emails
- Enter IDLE mode and wait for new emails
- Display a native notification for each GitHub email
- Mark the email as read after notification

Press `Ctrl-C` to stop.

### What you see

Each notification shows:
- **Title**: "GitHub"
- **Subtitle**: who did what (e.g., "alice requested your review on myorg/myrepo")
- **Message**: the PR or issue title

Clicking a notification opens the relevant GitHub page in your browser (the exact comment or review, not just the PR).

## Rules

Rules let you control which notifications fire and which are silently consumed. By default, all notifications fire.

Create `~/.config/octobell/rules.yml`:

```yaml
# Global rules (apply to all orgs unless overridden)
default:
  - reason: ci_activity
    action: skip
  - reason: subscribed
    action: skip

# Per-organization rules
rules:
  myorg:
    match:
      - reason: state_change
        action: skip
    repos:
      noisy-repo:
        - reason: comment
          action: skip
      legacy-app:
        - reason: subscribed
          action: notify  # override the global skip for this repo
```

### Actions

| Action | Behavior |
|--------|----------|
| `notify` | Display a desktop notification, mark email as read |
| `skip` | Mark email as read silently (no notification) |

### Rule evaluation order

Rules are evaluated from most specific to least specific. First match wins:

1. **Repo-level**: `rules.<org>.repos.<repo>`
2. **Org-level**: `rules.<org>.match`
3. **Global**: `default`
4. **Implicit default**: `notify` (if no rule matches)

### Available reasons

These correspond to the `X-GitHub-Reason` email header -- they describe *why* you received the notification:

| Reason | Meaning |
|--------|---------|
| `author` | Activity on a PR/issue you created |
| `review_requested` | You were asked to review a PR |
| `comment` | Activity on something you previously commented on |
| `mention` | You were @mentioned |
| `team_mention` | A team you belong to was @mentioned |
| `assign` | You were assigned |
| `subscribed` | Activity on a repo you're watching |
| `state_change` | A PR/issue was opened, closed, merged, or reopened |
| `ci_activity` | A CI workflow you triggered completed |

## Troubleshooting

### No notifications appearing

1. Check that `alerter` is installed: `which alerter`
2. Test alerter directly: `alerter --title "Test" --message "Hello" --json`
3. Run with debug logging: `OCTOBELL_LOG_LEVEL=DEBUG uv run python -m octobell`

### No emails detected

1. Confirm you have unread emails from `notifications@github.com` in your INBOX
2. Check that GitHub email notifications are enabled: GitHub > Settings > Notifications > Email
3. If using a Gmail label, try switching to `OCTOBELL_IMAP_FOLDER=INBOX`

### Authentication failed

- Gmail requires an [App Password](https://myaccount.google.com/apppasswords), not your regular password
- Ensure IMAP is enabled in your email provider's settings

### Connection drops

octobell automatically reconnects with exponential backoff (1s, 2s, 4s, ... up to 5 minutes). This is expected behavior when your network is unstable.

## Architecture

```
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

## License

MIT
