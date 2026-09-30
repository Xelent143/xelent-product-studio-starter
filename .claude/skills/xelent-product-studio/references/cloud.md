# Cloud sessions (Claude Code on the web)

The skill runs in a Claude Code cloud session the same way it runs on a computer. Customers start from the starter
repository https://github.com/Xelent143/xelent-product-studio-starter ("Use this template"), which already has the
skill in `.claude/skills/` (cloud sessions do not load installed plugins, only skills committed to the repository).

## What the environment needs
| Setting (claude.ai/code > environment) | Value |
|---|---|
| Network access | **Full** (research reads many websites; Xelent API is at xelentapi.com and api.xelentapi.com) |
| Environment variables | `XELENT_API_KEY=sk-...` (from https://xelentapi.com/dashboard/keys). Keep the environment private: anyone using it can read the value |

Node 20+ and Python 3 are installed. `pip install pillow openpyxl` works under Full network access.
Alibaba and Etsy are connected on https://xelentapi.com/dashboard/marketplaces, not in the session.

## Differences from a computer
- **Detect it:** `CLAUDE_CODE_REMOTE=true`. `board.py` prints a `CLOUD SESSION:` line after it builds boards.
- **Images:** `review/index.html` and `views.html` cannot be opened by the user. Show images as links:
  `python3 scripts/studio.py links --dir <workspace> --stage sheets|views|extras [--only <id> ...]` prints the newest
  version of every image per product, served from api.xelentapi.com for 7 days. Also commit and push `review/*.jpg`
  (boards are about 1 MB each) so GitHub displays them on the branch.
- **The machine can be wiped** some time after the session goes idle. Commit and push the workspace after every
  stage and approval: `studio.json`, `state.json`, `approvals.json`, `ledger.json`, `jobs.json`, `research/`,
  `listings/`, `published.json`, `review/*.jpg`. PNGs, `refs/` and `export/` stay out of git (too large).
- **Missing images after a wipe:** run `node scripts/run.mjs --dir <workspace> --restore` first. It reads
  `ledger.json` and downloads every image already made and paid for, from every stage, for free. Images older than
  7 days are gone from Xelent; plan and run that stage again to make them (`run.mjs --quote` shows the cost first).
  A normal `run.mjs` also downloads the current stage's paid images again before it submits anything.
- **Command time:** a foreground command gets up to 10 minutes; start `run.mjs` in the background for big stages
  and poll `run.mjs --status`.
