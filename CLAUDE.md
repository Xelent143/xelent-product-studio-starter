# Xelent Product Studio workspace

This repository is a workspace for the Xelent skills in `.claude/skills/`: `xelent-product-studio` for research,
product designs, product photos and Etsy and Alibaba listings, and `xelent-product-video` for product videos.

- Workspace folders: `product-studio/` (created by `studio.py init`) and `product-video/<name>/` (created by
  `video.py init`). Final videos in `product-video/*/final/` are committed so the user can download them.
- This usually runs as a cloud session (Claude Code on the web). Follow the skill's "Cloud sessions" section:
  the API key comes from `XELENT_API_KEY`, the user sees images as links, and progress is committed and pushed
  after every stage and approval because the machine can be wiped while the user is away.
- The user may not be technical. Run every command yourself and explain results in plain words.
- To update the skills when the user asks: replace the folders in `.claude/skills/` with the same folders from
  https://github.com/Xelent143/xelent-product-studio-starter (main branch), then commit and push.
