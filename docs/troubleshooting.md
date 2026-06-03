# Troubleshooting

## No notifications appearing

1. Check that `alerter` is installed: `which alerter`
2. Test alerter directly: `alerter --title "Test" --message "Hello" --json`
3. Run with debug logging: `OCTOBELL_LOG_LEVEL=DEBUG uv run python -m octobell`

## No emails detected

1. Confirm you have unread emails from `notifications@github.com` in your INBOX
2. Check that GitHub email notifications are enabled: GitHub > Settings > Notifications > Email
3. If using a Gmail label, try switching to `INBOX` in your folders list

## Authentication failed

- Gmail requires an [App Password](https://myaccount.google.com/apppasswords), not your regular password
- Ensure IMAP is enabled in your email provider's settings

## Connection drops

octobell automatically reconnects with exponential backoff (1s, 2s, 4s, ... up to 5 minutes). This is expected behavior when your network is unstable.
