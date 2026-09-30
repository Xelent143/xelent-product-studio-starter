# Xelent Product Studio workspace

This repository is a workspace for the `xelent-product-studio` skill in `.claude/skills/`. Use that skill for
everything the user asks here: research, product designs, product photos, Etsy and Alibaba listings.

- The workspace folder is `product-studio/` (create it with the skill's `studio.py init` on first use).
- This usually runs as a cloud session (Claude Code on the web). Follow the skill's "Cloud sessions" section:
  the API key comes from `XELENT_API_KEY`, the user sees images as links, and progress is committed and pushed
  after every stage and approval because the machine can be wiped while the user is away.
- The user may not be technical. Run every command yourself and explain results in plain words.
- To update the skill when the user asks: replace `.claude/skills/xelent-product-studio/` with the same folder from
  https://github.com/Xelent143/xelent-product-studio-starter (main branch), then commit and push.
