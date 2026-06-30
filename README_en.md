# Markdown Platform Publisher Skill

[中文](README.md) | English

`markdown-platform-publisher` turns Markdown articles that contain local images into platform-ready Markdown for CSDN, Juejin, Zhihu, BlogCN, WeChat editors, and similar platforms.

The default workflow uses **PicList's local HTTP server** to upload images to the image host currently configured in PicList, such as **Cloudflare R2**, then rewrites local image paths into public HTTPS image URLs.

It is designed for the common CSDN problem where Markdown imports fail with external image transfer errors when images are local paths or unstable GitHub/jsDelivr links.

## What It Does

- Scans Markdown images: `![alt](image.png)`
- Scans HTML images: `<img src="image.png">`
- Skips remote images such as `https://...`, `data:`, and protocol-relative URLs
- Skips fenced code block examples and placeholders such as `{{image}}`
- Uploads real local images through PicList
- Creates one remote folder per article, for example:

```text
articles/coze-multi-platform-copywriting-assistant-blog-1/
```

- Stages images with ASCII filenames before upload, avoiding URL mojibake from Chinese filenames
- Generates a CSDN-ready Markdown file with HTTPS image links
- Generates `.image-map.json` and `.publish-report.json`
- Can verify returned public image URLs with HTTP checks

## Requirements

1. Install and configure PicList.
2. Configure a PicList uploader, for example Cloudflare R2 through the S3-compatible uploader.
3. Enable PicList's built-in server.
4. Know your PicList upload endpoint and final public image URL prefix.

Typical PicList endpoint:

```text
http://127.0.0.1:36677/upload
```

Typical Cloudflare R2 public URL prefix:

```text
https://pub-xxxx.r2.dev
```

Do not use a Cloudflare dashboard URL as the public URL. Use the actual public R2 URL or custom domain that browsers and CSDN can access.

Setup guide:

[Cloudflare R2 + PicList Setup Guide](docs/cloudflare-r2-piclist-setup.md)

## Basic Usage

Windows:

```powershell
python scripts\publish_markdown_piclist.py --input "D:\path\to\article.md" --expected-url-prefix "https://pub-xxxx.r2.dev" --check-links --keep-staged
```

macOS / Linux:

```bash
python scripts/publish_markdown_piclist.py --input "/path/to/article.md" --expected-url-prefix "https://pub-xxxx.r2.dev" --check-links --keep-staged
```

Successful output looks like:

```json
{
  "asset_prefix": "articles/my-article-slug/",
  "unique_assets": 4,
  "validation": {
    "original_local_image_refs": 4,
    "rewritten_remote_refs": 4,
    "remaining_local_image_refs": 0
  }
}
```

Generated files:

```text
article（PicList发布版）.md
article（PicList发布版）.image-map.json
article（PicList发布版）.publish-report.json
article（PicList发布版）.piclist-staged/
```

The staged folder is kept when `--keep-staged` is used. It shows the ASCII filenames that were uploaded.

## Per-Article Folders

By default, the script derives an English slug from the Markdown filename and temporarily sets PicList's `uploadPath` to:

```text
articles/<slug>/
```

Example input filename:

```text
Coze多平台文案创作助手博客 - 1.md
```

Example remote path:

```text
articles/coze-multi-platform-copywriting-assistant-blog-1/
```

You can override it explicitly:

```powershell
python scripts\publish_markdown_piclist.py --input "D:\path\to\article.md" --slug "my-custom-article" --expected-url-prefix "https://pub-xxxx.r2.dev" --check-links --keep-staged
```

The script restores the original PicList config after upload, even if an upload fails.

## API-Key Protected PicList Server

If your PicList server uses an API key:

```powershell
python scripts\publish_markdown_piclist.py --input "D:\path\to\article.md" --endpoint "http://127.0.0.1:36677/upload?key=YOUR_KEY" --expected-url-prefix "https://pub-xxxx.r2.dev" --check-links --keep-staged
```

## Options

```text
--input                 Input Markdown file.
--output                Output Markdown file. Defaults to <name>（PicList发布版）.md.
--endpoint              PicList upload endpoint. Default: http://127.0.0.1:36677/upload.
--asset-root            Remote root path. Default: articles.
--slug                  Article directory name under --asset-root.
--piclist-config        PicList data.json path. By default, the script auto-detects:
                        macOS: ~/Library/Application Support/piclist/data.json
                        Windows: %APPDATA%\piclist\data.json
                        Linux: ~/.config/piclist/data.json
--no-set-upload-path    Do not change PicList uploadPath; use current PicList config.
--expected-url-prefix   Expected public image URL prefix, for example https://pub-xxxx.r2.dev.
--check-links           Check returned public image URLs after upload.
--timeout               Upload/check timeout per image. Default: 120 seconds.
--keep-staged           Keep staged ASCII-named upload files next to the output.
```

## Codex Usage

After installing this skill, you can ask Codex directly:

```text
把这个 md 文档转成 CSDN 可导入的 Markdown，图片走 PicList/R2 图床。
```

Provide:

- the Markdown file path
- the PicList local upload endpoint, if it is not the default
- the final R2 public URL prefix

Codex will run the script, verify the result, and return the generated Markdown path.

## GitHub/jsDelivr Fallback

The old GitHub workflow is still available for users who explicitly want it:

```powershell
python scripts\publish_markdown.py --input "D:\path\to\article.md" --repo "owner/blog-assets"
```

However, PicList/R2 is recommended for CSDN imports because GitHub/jsDelivr external image transfer can be unreliable.

## Troubleshooting

If PicList is not reachable:

- Open PicList.
- Enable the built-in server.
- Confirm the server port, usually `36677`.

If upload fails:

- Check PicList's selected uploader.
- Check Cloudflare R2 credentials and bucket settings.
- Check the public URL prefix.
- Inspect PicList logs:
  - macOS: usually under `~/Library/Application Support/piclist/`
  - Windows: usually under `%APPDATA%\piclist\`
  - Linux: usually under `~/.config/piclist/`

If generated image URLs do not open in a browser, do not import the Markdown into CSDN yet. Fix R2 public access or PicList custom URL settings first.
