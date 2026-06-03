# Configuration

octobell reads YAML config files from `~/.config/octobell/`. Each `.yml` file defines one IMAP account to watch. On first run, a template file is created for you.

## Single account

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

## Multiple accounts [**Untested**]

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

## Gmail setup

1. Enable 2-Step Verification on your Google account
2. Go to [App passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Enable IMAP in Gmail: Settings > Forwarding and POP/IMAP > Enable IMAP

## Rules

You can define rules per account to control which notifications fire and which are silently consumed. See the [rules documentation](rules.md) for details.
