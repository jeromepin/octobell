# octobell

Native desktop notifications for GitHub, powered by your email inbox.

octobell connects to your email account(s) via IMAP, watches for GitHub notification emails in near-realtime using IMAP IDLE, and fires native macOS or Linux notifications. Click a notification to open the relevant PR or comment in your browser.

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

octobell reads YAML config files from `~/.config/octobell/`. Each `.yml` file defines one IMAP account to watch. On first run, a template file is created for you.

### Single account

Create `~/.config/octobell/personal.yml`:

```yaml
imap:
  host: imap.gmail.com
  port: 993
  user: you@gmail.com
  password: xxxx-xxxx-xxxx-xxxx
  folders:
    - INBOX
```

### Multiple accounts

GitHub lets you route each organization's notifications to a different email address. Create one file per account:

```yaml
# ~/.config/octobell/personal.yml
imap:
  host: imap.gmail.com
  user: you@gmail.com
  password: xxxx-xxxx-xxxx-xxxx
  folders:
    - INBOX
```

```yaml
# ~/.config/octobell/work.yml
imap:
  host: imap.gmail.com
  user: you@company.com
  password: yyyy-yyyy-yyyy-yyyy
  folders:
    - INBOX
    - GitHub
```

octobell watches all accounts simultaneously, each in its own thread.

### Gmail setup

1. Enable 2-Step Verification on your Google account
2. Go to [App passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Enable IMAP in Gmail: Settings > Forwarding and POP/IMAP > Enable IMAP

### Other providers

Any IMAP provider works. Use your provider's IMAP hostname and port. Examples:

| Provider | Host | Port |
|----------|------|------|
| Gmail | `imap.gmail.com` | 993 |
| Outlook | `outlook.office365.com` | 993 |
| Fastmail | `imap.fastmail.com` | 993 |
| ProtonMail (Bridge) | `127.0.0.1` | 1143 |

## Usage

```bash
uv run python -m octobell
```

Set log level with the `OCTOBELL_LOG_LEVEL` environment variable (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default is `INFO`.

octobell will:
- Connect to all configured IMAP accounts
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

Rules let you control which notifications fire and which are silently consumed. Rules are defined per account, inside the same YAML config file. By default, all notifications fire.

```yaml
# ~/.config/octobell/work.yml
imap:
  host: imap.gmail.com
  user: you@company.com
  password: yyyy-yyyy-yyyy-yyyy
  folders:
    - INBOX

rules:
  # Global rules (apply to all orgs in this account unless overridden)
  default:
    - reason: ci_activity
      action: skip
    - reason: subscribed
      action: skip

  # Per-organization rules
  orgs:
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

1. **Repo-level**: `rules.orgs.<org>.repos.<repo>`
2. **Org-level**: `rules.orgs.<org>.match`
3. **Global**: `rules.default`
4. **Implicit default**: `notify` (if no rule matches)

### Available reasons

The **reason** (from the `X-GitHub-Reason` email header) describes *why* you received the notification:

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

### Available events

The **event** (parsed from the email body) describes *what* happened. It is optional — omit it to match any event for a given reason.

| Event | Meaning |
|-------|---------|
| `pr_opened` | A new pull request was created |
| `review_requested` | Someone requested your review |
| `comment` | Someone left a comment |
| `approved` | Someone approved the PR |
| `changes_requested` | Someone requested changes |
| `merged` | The PR was merged |
| `closed` | The PR/issue was closed |
| `reopened` | The PR/issue was reopened |
| `push` | Someone pushed commits |
| `review_dismissed` | A review was dismissed |

### Reason × Event matrix

Each GitHub notification email combines a **reason** (why you're subscribed) with an **event** (what happened). This matrix shows which combinations are possible and what they mean.

| Reason ↓ \ Event → | `pr_opened` | `review_requested` | `comment` | `approved` | `changes_requested` | `merged` | `closed` | `push` | `reopened` | `review_dismissed` |
|---|---|---|---|---|---|---|---|---|---|---|
| `author` | | | someone commented on your PR | someone approved your PR | someone requested changes on your PR | someone merged your PR | someone closed your PR | someone pushed to your PR | someone reopened your PR | a review was dismissed on your PR |
| `review_requested` | PR was opened, you're a reviewer | you were asked to review | someone commented | someone approved | someone requested changes | PR was merged | PR was closed | someone pushed commits | | |
| `comment` | | | someone commented | someone approved | someone requested changes | PR was merged | PR was closed | someone pushed commits | someone reopened | |
| `mention` | | | you were @mentioned | | | | | | | |
| `team_mention` | | | your team was @mentioned | | | | | | | |
| `assign` | | | someone commented | someone approved | someone requested changes | PR was merged | PR was closed | someone pushed commits | | |
| `subscribed` | new PR in a watched repo | | someone commented | someone approved | someone requested changes | PR was merged | PR was closed | someone pushed commits | someone reopened | |
| `state_change` | | | | | | PR was merged | PR was closed | | PR was reopened | |
| `ci_activity` | | | | | | | | | | |

Empty cells are unlikely or impossible combinations. `ci_activity` events are CI-specific and don't map to standard event types.

### Example rules

```yaml
rules:
  default:
    # Skip ALL activity on PRs where your review was requested
    - reason: review_requested
      action: skip

    # Skip only comments on PRs where your review was requested
    # (still notified for: review request, approval, changes requested, merge)
    - reason: review_requested
      event: comment
      action: skip

    # Skip the redundant "PR opened" email when your review is requested
    # (you still get the actual "requested your review" notification)
    - reason: review_requested
      event: pr_opened
      action: skip

    # Skip all activity on things you're watching
    - reason: subscribed
      action: skip

    # Skip CI notifications entirely
    - reason: ci_activity
      action: skip

    # Skip only merges on things you previously commented on
    - reason: comment
      event: merged
      action: skip
```

## Troubleshooting

### No notifications appearing

1. Check that `alerter` is installed: `which alerter`
2. Test alerter directly: `alerter --title "Test" --message "Hello" --json`
3. Run with debug logging: `OCTOBELL_LOG_LEVEL=DEBUG uv run python -m octobell`

### No emails detected

1. Confirm you have unread emails from `notifications@github.com` in your INBOX
2. Check that GitHub email notifications are enabled: GitHub > Settings > Notifications > Email
3. If using a Gmail label, try switching to `INBOX` in your folders list

### Authentication failed

- Gmail requires an [App Password](https://myaccount.google.com/apppasswords), not your regular password
- Ensure IMAP is enabled in your email provider's settings

### Connection drops

octobell automatically reconnects with exponential backoff (1s, 2s, 4s, ... up to 5 minutes). This is expected behavior when your network is unstable.

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

## License

MIT
