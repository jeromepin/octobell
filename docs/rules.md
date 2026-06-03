# Rules

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

## Actions

| Action | Behavior |
|--------|----------|
| `notify` | Display a desktop notification, mark email as read |
| `skip` | Mark email as read silently (no notification) |

## Rule evaluation order

Rules are evaluated from most specific to least specific. First match wins:

1. **Repo-level**: `rules.orgs.<org>.repos.<repo>`
2. **Org-level**: `rules.orgs.<org>.match`
3. **Global**: `rules.default`
4. **Implicit default**: `notify` (if no rule matches)

## Available reasons

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

## Available events

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

## Reason × Event matrix

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

## Example rules

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
