---
name: markdown-platform-publisher
description: Publish Markdown articles with local images to CSDN, Juejin, Zhihu, BlogCN, WeChat editors, or other blog platforms by uploading local image assets through PicList's local HTTP server to the user's configured image host such as Cloudflare R2, rewriting Markdown image links to public HTTPS URLs, and validating a platform-ready Markdown output. Use when the user asks to output, convert, export, prepare, or make a Markdown article/blog/tutorial/document suitable for CSDN or blog platform upload, fix local/failed image transfer issues, replace local Markdown images with HTTPS image-host links, or generate a publish-ready md file. If the user explicitly requests GitHub/jsDelivr, use the GitHub fallback script instead.
---

# Markdown Platform Publisher

## Overview

Use this skill to turn a Markdown article with local images into a platform-ready Markdown file. The default workflow uploads local images through the user's running PicList local server, rewrites image references to public HTTPS image-host URLs, and emits a validated PicList publish version plus mapping/report files. By default, each article gets its own remote directory under `articles/<english-article-slug>/` instead of reusing a shared folder.

Prefer PicList/Cloudflare R2 for CSDN/platform publishing workflows because GitHub/jsDelivr links can be unstable during CSDN external image transfer.

Default PicList endpoint:

```text
http://127.0.0.1:36677/upload
```

The user should provide or confirm the final public image URL prefix, for example:

```text
https://pub-xxxx.r2.dev
```

## Preferred Workflow

1. Identify the input Markdown file. If several candidate `.md` files exist and the user did not specify one, ask which file to publish.
2. Confirm PicList is configured with the intended image host and ask for the PicList upload endpoint and public image URL prefix if not already known.
3. Verify PicList is running by requesting `http://127.0.0.1:36677/` or checking port `36677`.
4. Run the PicList script:

```bash
python <SKILL_ROOT>/scripts/publish_markdown_piclist.py \
  --input "/path/to/article.md" \
  --endpoint "http://127.0.0.1:36677/upload" \
  --expected-url-prefix "https://pub-xxxx.r2.dev" \
  --asset-root "articles" \
  --check-links \
  --keep-staged
```

5. Inspect the script summary. A successful run must report:
   - `original_local_image_refs` equals the number of real local image references found.
   - `rewritten_remote_refs` equals the number of uploaded images.
   - `remaining_local_image_refs` is `0`.
   - `asset_prefix` is `articles/<english-article-slug>/` unless the user supplied another `--asset-root` or `--slug`.
   - `link_checks` has HTTP `200` image responses when `--check-links` is used.
6. Return the output file path and mention that the generated Markdown is the PicList/R2 platform publishing version. Do not publish the article to a platform unless the user explicitly asks for that.

## PicList Script Behavior

`scripts/publish_markdown_piclist.py` handles:

- Markdown images: `![alt](image.png)`
- HTML images: `<img src="image.png">`
- URL-encoded local paths: `image%201.png`
- Relative images under subfolders
- Already-remote `http`, `https`, `data:`, and protocol-relative images by leaving them unchanged
- Fenced code blocks by skipping image syntax inside examples
- Placeholder image references such as `{{image}}` and `image link` by leaving them unchanged
- A per-article remote directory such as `articles/coze-multi-platform-copywriting-assistant-blog-1/`, derived from the Markdown filename unless `--slug` is provided
- Temporary ASCII staged filenames such as `01-cover.png` and `02-image.png` before upload, avoiding CSDN/PicList issues caused by non-ASCII filenames or URL mojibake
- Temporary PicList `uploadPath` override: it updates PicList's local `data.json`, uploads images, and restores the original config even when upload fails
- `image-map.json` and `publish-report.json` beside the output Markdown

Default output name:

```text
<original-stem> (PicList publish version).md
```

The actual filename produced by the script uses the localized suffix configured in the script.

## Common Commands

Publish with default PicList endpoint and public URL check:

```bash
python <SKILL_ROOT>/scripts/publish_markdown_piclist.py \
  --input "/path/to/article.md" \
  --expected-url-prefix "https://pub-xxxx.r2.dev" \
  --check-links \
  --keep-staged
```

Publish with an explicit article directory slug:

```bash
python <SKILL_ROOT>/scripts/publish_markdown_piclist.py \
  --input "/path/to/article.md" \
  --slug "my-english-article-name" \
  --expected-url-prefix "https://pub-xxxx.r2.dev" \
  --check-links \
  --keep-staged
```

Publish with an explicit PicList endpoint or API key:

```bash
python <SKILL_ROOT>/scripts/publish_markdown_piclist.py \
  --input "/path/to/article.md" \
  --endpoint "http://127.0.0.1:36677/upload?key=YOUR_KEY" \
  --expected-url-prefix "https://pub-xxxx.r2.dev" \
  --check-links \
  --keep-staged
```

## GitHub Fallback

Only use the GitHub/jsDelivr workflow when the user explicitly asks for GitHub, jsDelivr, or the old behavior. Run:

```bash
python <SKILL_ROOT>/scripts/publish_markdown.py \
  --input "/path/to/article.md" \
  --repo "owner/blog-assets"
```

GitHub fallback uploads local images to a public GitHub asset repository, commits/pushes them, and rewrites image references to `https://cdn.jsdelivr.net/gh/...` URLs. Treat it as a fallback because CSDN may fail external image transfer from GitHub/jsDelivr.

## Failure Handling

If PicList is not running or port `36677` is closed, ask the user to open PicList and enable its built-in server, then retry.

If PicList returns `success: false`, read the latest PicList log. On Windows, the default path is:

```text
%APPDATA%\piclist\piclist.log
```

Report the exact error and ask the user to confirm PicList's selected uploader, Cloudflare R2 credentials, bucket, path, endpoint, and custom public URL.

If a local image is missing, stop before uploading and list missing paths. Do not generate a partially rewritten Markdown unless the user asks for a partial output.

If uploaded URLs contain garbled non-ASCII filenames, rerun the PicList script; it stages images with ASCII filenames specifically to avoid this problem.

If generated URLs are not reachable, do not hand the file off as CSDN-ready. Verify Cloudflare R2 public access/custom domain and PicList custom URL settings first.
