# Markdown Platform Publisher Skill

中文 | [English](README_en.md)

`markdown-platform-publisher` 是一个用于把带本地图片的 Markdown 文章转换成平台可导入版本的 Codex Skill，适合发布到 CSDN、掘金、知乎、博客园、微信公众号编辑器等平台。

默认工作流使用 **PicList 本地上传接口**，把文章里的本地图片上传到你已经在 PicList 中配置好的图床，例如 **Cloudflare R2**，然后把 Markdown 中的本地图片路径替换成公开 HTTPS 图片链接。

这个 Skill 主要解决 CSDN 导入 Markdown 时常见的图片问题：本地图片无法显示、GitHub/jsDelivr 外链转存失败、中文图片文件名导致 URL 乱码等。

## 功能

- 识别 Markdown 图片：`![alt](image.png)`
- 识别 HTML 图片：`<img src="image.png">`
- 跳过已经是远程地址的图片，例如 `https://...`、`data:`、协议相对地址
- 跳过代码块里的示例图片语法和 `{{image}}` 这类占位符
- 通过 PicList 上传真实存在的本地图片
- 按文章自动创建独立远程目录，例如：

```text
articles/coze-multi-platform-copywriting-assistant-blog-1/
```

- 上传前把图片暂存为 ASCII 文件名，避免中文文件名在 CSDN/PicList/URL 中出现乱码
- 生成 CSDN 可导入的 Markdown 文件
- 生成 `.image-map.json` 和 `.publish-report.json`，方便追踪图片映射和发布结果
- 可选检查上传后的公开图片链接是否能正常访问

## 准备工作

1. 安装并配置 PicList。
2. 在 PicList 中配置图床，例如通过 Amazon S3 兼容配置连接 Cloudflare R2。
3. 打开 PicList 的内置 Server。
4. 准备好 PicList 本地上传接口和最终公开图片域名。

常见 PicList 上传接口：

```text
http://127.0.0.1:36677/upload
```

常见 Cloudflare R2 公开图片域名：

```text
https://pub-xxxx.r2.dev
```

注意：不要把 Cloudflare 控制台地址当成公开图片域名。这里要填写浏览器和 CSDN 都能直接访问图片的 R2 公开地址或自定义域名。

Cloudflare R2 + PicList 的 Windows 配置教程见：

[Cloudflare R2 + PicList 配置教程](docs/cloudflare-r2-piclist-setup.md)

## 基础用法

```powershell
python scripts\publish_markdown_piclist.py --input "D:\path\to\article.md" --expected-url-prefix "https://pub-xxxx.r2.dev" --check-links --keep-staged
```

成功后会输出类似结果：

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

生成文件示例：

```text
article（PicList发布版）.md
article（PicList发布版）.image-map.json
article（PicList发布版）.publish-report.json
article（PicList发布版）.piclist-staged/
```

使用 `--keep-staged` 时会保留 `.piclist-staged/` 暂存目录，里面是上传前转换好的 ASCII 图片文件名。

## 每篇文章独立目录

脚本会默认根据 Markdown 文件名生成英文 slug，并临时把 PicList 的 `uploadPath` 设置成：

```text
articles/<slug>/
```

例如输入文件名：

```text
Coze多平台文案创作助手博客 - 1.md
```

对应远程目录可能是：

```text
articles/coze-multi-platform-copywriting-assistant-blog-1/
```

也可以手动指定目录名：

```powershell
python scripts\publish_markdown_piclist.py --input "D:\path\to\article.md" --slug "my-custom-article" --expected-url-prefix "https://pub-xxxx.r2.dev" --check-links --keep-staged
```

脚本会在上传结束后恢复 PicList 原来的配置，即使上传失败也会尝试恢复。

## PicList Server 带 API Key 的情况

如果你的 PicList Server 设置了 API Key，可以把 key 放在上传接口里：

```powershell
python scripts\publish_markdown_piclist.py --input "D:\path\to\article.md" --endpoint "http://127.0.0.1:36677/upload?key=YOUR_KEY" --expected-url-prefix "https://pub-xxxx.r2.dev" --check-links --keep-staged
```

## 参数说明

```text
--input                 输入 Markdown 文件。
--output                输出 Markdown 文件，默认生成 <原文件名>（PicList发布版）.md。
--endpoint              PicList 上传接口，默认 http://127.0.0.1:36677/upload。
--asset-root            远程根目录，默认 articles。
--slug                  文章目录名，位于 --asset-root 下。
--piclist-config        PicList data.json 路径，Windows 默认读取 %APPDATA%\piclist\data.json。
--no-set-upload-path    不修改 PicList uploadPath，直接使用当前 PicList 配置。
--expected-url-prefix   期望的公开图片 URL 前缀，例如 https://pub-xxxx.r2.dev。
--check-links           上传后检查公开图片链接是否可访问。
--timeout               单张图片上传/检查超时时间，默认 120 秒。
--keep-staged           保留上传前的 ASCII 文件名暂存目录。
```

## 在 Codex 中使用

安装这个 Skill 后，可以直接对 Codex 说：

```text
把这个 md 文档转成 CSDN 可导入的 Markdown，图片走 PicList/R2 图床。
```

建议同时提供：

- Markdown 文件路径
- PicList 本地上传接口，不提供时默认使用 `http://127.0.0.1:36677/upload`
- R2 最终公开图片域名，例如 `https://pub-xxxx.r2.dev`

Codex 会运行脚本、检查结果，并返回生成后的 Markdown 文件路径。

## GitHub/jsDelivr 备用方案

如果你明确想继续使用 GitHub 图床，也可以使用旧脚本：

```powershell
python scripts\publish_markdown.py --input "D:\path\to\article.md" --repo "owner/blog-assets"
```

不过对于 CSDN 导入场景，更推荐 PicList/R2，因为 GitHub/jsDelivr 外链在 CSDN 图片转存时可能不稳定。

## 常见问题

如果提示 PicList 无法连接：

- 打开 PicList。
- 开启内置 Server。
- 确认端口，通常是 `36677`。

如果上传失败：

- 检查 PicList 当前选择的图床。
- 检查 Cloudflare R2 的 Access Key、Secret Key、Bucket、Endpoint。
- 检查 R2 公开访问域名是否正确。
- 查看 PicList 日志，Windows 通常在 `%APPDATA%\piclist\piclist.log`。

如果生成后的图片链接在浏览器里打不开，先不要导入 CSDN。需要先修好 R2 公开访问或 PicList 自定义域名配置。
