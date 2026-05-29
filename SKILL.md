---
name: markdown-platform-publisher
description: Publish Markdown articles with local images to CSDN, Juejin, Zhihu, BlogCN, WeChat editors, or other blog platforms by uploading local image assets to a public GitHub repository, generating jsDelivr HTTPS image URLs, rewriting Markdown image links, and validating a platform-ready Markdown output. Use when the user asks to output, convert, export, prepare, or make a Markdown article/blog/tutorial/document suitable for CSDN or blog platform upload; examples include "输出为 CSDN", "平台发布版", "博客平台文档", "适合上传到 CSDN", "修复 Markdown 图片转存失败", "把本地图片改成图床链接", "生成可发布 md", "发布到掘金/知乎/博客园", "convert this markdown for blog platforms", or "rewrite markdown images to HTTPS".
---

# Markdown Platform Publisher

## Overview

Use this skill to turn a Markdown tutorial or blog article that contains local images into a platform-ready Markdown file. The workflow uploads local image files to a public GitHub asset repository, rewrites image references to jsDelivr HTTPS URLs, and emits a validated `（平台发布版）.md` file plus mapping/report files.

Prefer the bundled script for the whole workflow:

```bash
python3 <SKILL_ROOT>/scripts/publish_markdown.py \
  --input "/path/to/article.md" \
  --repo "STRUGGLE1999/blog-assets"
```

## Repository Selection

Use `STRUGGLE1999/blog-assets` as the default repository for Xiaolifang's personal workflows when the user asks in this workspace to make an article suitable for CSDN or platform publishing and does not provide another repo.

For other users, or when a repo is not obvious, ask for a public GitHub repository such as `yourname/blog-assets`. The repository must be public for jsDelivr links to work. The user must have Git push credentials configured locally.

Accept repository inputs in any of these forms:

- `owner/repo`
- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`

## Workflow

1. Identify the input Markdown file. If several candidate `.md` files exist and the user did not specify one, ask which file to publish.
2. Run the script with the selected Markdown file and repo.
3. Let the script clone the GitHub repo into a temporary directory, copy local images into `articles/<article-slug>/`, commit, push, and use the resulting commit hash in jsDelivr URLs.
4. Inspect the script summary. A successful run must report no local image references left and equal original/rewritten image counts.
5. Return the output file path and mention the GitHub commit. Do not publish the article to a platform unless the user explicitly asks for that.

## Script Behavior

The script handles:

- Markdown images: `![alt](image.png)`
- URL-encoded local paths: `image%201.png`
- HTML images: `<img src="image.png">`
- Relative images under subfolders
- Already-remote `http`, `https`, `data:`, and protocol-relative images by leaving them unchanged
- Stable asset names like `01-codex-plugin-entry.png`
- `image-map.json` and `publish-report.json` beside the output Markdown
- Optional `--check-links` HTTP validation for generated jsDelivr URLs

Default output name:

```text
<original-stem>（平台发布版）.md
```

Default CDN URL form:

```text
https://cdn.jsdelivr.net/gh/<owner>/<repo>@<commit>/articles/<article-slug>/<image-file>
```

Use commit-hash URLs instead of `@main` so published articles stay stable even if future images change.

## Common Trigger Phrases

Treat these as requests to use this skill:

- `把这篇文章输出为支持 CSDN 的博客`
- `生成 CSDN 发布版 md`
- `生成平台发布版 Markdown`
- `把这篇教程改成适合上传到 CSDN`
- `把 Markdown 里的本地图片换成 HTTPS 图床链接`
- `修复 CSDN 图片转存失败`
- `做一份可导入 CSDN / 掘金 / 知乎的版本`
- `输出为博客平台文档`
- `把这篇博文整理成各平台可发布版本`
- `make this markdown ready for CSDN`
- `convert local markdown images to jsDelivr links`

## Failure Handling

If GitHub clone or push fails, report the exact failure and keep any generated temporary asset mapping if available. Ask the user to confirm repository visibility, local Git credentials, or repo write permission.

If a local image is missing, stop before uploading and list missing paths. Do not generate a partially rewritten Markdown unless the user asks for a partial output.

If jsDelivr has a temporary cache delay, the GitHub push can still be correct. Use GitHub raw URLs as a diagnostic only; keep jsDelivr URLs in the final Markdown unless the user asks otherwise.
