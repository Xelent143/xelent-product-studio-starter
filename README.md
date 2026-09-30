# Xelent Product Studio: starter for Claude Code on the web

Research an apparel segment, design new products, photograph them and list them on Etsy and Alibaba.com, all from
your browser at [claude.ai/code](https://claude.ai/code). Nothing to install on your computer.

This repository is a ready workspace: it carries the
[Xelent Product Studio](https://github.com/Xelent143/xelent-product-studio) skill in `.claude/skills/`, which is
where Claude Code on the web looks for it. Images are made with [Xelent API](https://xelentapi.com) credits.

## What you need

- A Claude plan that includes Claude Code on the web (Pro, Max, Team or Enterprise) and a GitHub account.
- A Xelent API account with credits and an API key: [xelentapi.com/dashboard/keys](https://xelentapi.com/dashboard/keys).
- To submit listings: Etsy and Alibaba connected at [xelentapi.com/dashboard/marketplaces](https://xelentapi.com/dashboard/marketplaces)
  ([step-by-step guide](https://xelentapi.com/help/marketplaces)).

## Set up (once, about 5 minutes)

1. **Make your own copy.** Click **Use this template** > **Create a new repository** at the top of this page. Choose
   **Private**, give it a name (for example `my-product-studio`) and create it.
2. **Open [claude.ai/code](https://claude.ai/code)** and connect GitHub when it asks. Pick your new repository.
3. **Set up the cloud environment.** Open the environment menu, then select **Add cloud environment** (or hover over
   your environment and select its settings icon) and set:
   - **Network access:** **Full**. The research step reads many websites, and images come from xelentapi.com.
   - **Environment variables:** one line, with your own key:
     ```
     XELENT_API_KEY=sk-your-key-here
     ```
     Keep this environment to yourself: anyone who uses it can read the key.
4. **Start a session** in that environment and say what you want, for example:
   > Research the teamwear market and design 5 new football jerseys for my brand "Northfield". Then list them on
   > Etsy as drafts.

## What happens next

- Claude asks a few questions first: your brand, what your factory can make, and whether you want photos at
  **2K** (Nano Banana 2) or **4K** (GPT Image 2.5 Sunburst).
- Before every batch of images it tells you how many images, the credits they will use and your balance after.
  After the batch it tells you the credits used and the credits left.
- It shows the designs as image links for you to approve or change. Nothing is photographed before you approve the
  design sheet, and nothing is submitted to Etsy or Alibaba until you approve the listing and say "submit".
- To put your logo on the products, upload the logo file to your repository first (on GitHub: **Add file** >
  **Upload files**) and tell Claude its name.
- Your work is saved to your repository after each step, so you can close the tab and continue later. Image files
  stay on Xelent for 7 days; download anything you want to keep.

## Keeping the skill up to date

The skill in `.claude/skills/xelent-product-studio/` is copied from
[Xelent143/xelent-product-studio](https://github.com/Xelent143/xelent-product-studio). To update your copy, ask
Claude in a session: "Update the xelent-product-studio skill from the Xelent143/xelent-product-studio-starter
template".

## Help

Support: [support@xelentapi.com](mailto:support@xelentapi.com). Guide:
[xelentapi.com/help/claude-code-web](https://xelentapi.com/help/claude-code-web).
