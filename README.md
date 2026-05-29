# Markdown Platform Publisher Skill

`markdown-platform-publisher` 是一个 Codex Skill，用来把带有本地图片的 Markdown 教程、博客或文档转换成适合 CSDN、掘金、知乎、博客园、微信公众号编辑器等平台导入的发布版 Markdown。

它会自动扫描 Markdown 里的本地图片，上传到公开 GitHub 图床仓库，通过 jsDelivr 生成 HTTPS 图片链接，然后回写 Markdown，输出一份 `（平台发布版）.md`。

## 适合解决什么问题

很多博客平台导入 Markdown 时，只能正常显示文字，图片会因为仍然是本地路径而转存失败，例如：

```md
![截图](image.png)
![步骤图](image%201.png)
```

这个 Skill 会把它们改成平台可访问的 HTTPS 图片链接：

```md
![截图](https://cdn.jsdelivr.net/gh/yourname/blog-assets@commit/articles/article-slug/01-screenshot.png)
```

## 核心功能

- 扫描 Markdown 图片：`![alt](image.png)`
- 扫描 HTML 图片：`<img src="image.png">`
- 支持 URL 编码路径：`image%201.png`
- 跳过已有远程图片：`https://...`、`data:` 等
- 上传图片到公开 GitHub 仓库
- 使用 jsDelivr 生成 HTTPS 图片链接
- 使用 commit hash 固定资源版本，而不是不稳定的 `@main`
- 生成平台发布版 Markdown
- 生成图片映射表和发布报告
- 可选 HTTP 检查生成的图片链接是否可访问

## 触发方式

在 Codex 里可以这样说：

```text
把这篇文章输出为支持 CSDN 的博客
```

也可以这样说：

```text
生成 CSDN 发布版 md
```

```text
把 Markdown 里的本地图片换成 HTTPS 图床链接
```

```text
做一份可导入 CSDN / 掘金 / 知乎的版本
```

```text
把这篇博文整理成各平台可发布版本
```

英文也可以：

```text
make this markdown ready for CSDN
```

```text
convert local markdown images to jsDelivr links
```

## 使用前准备

你需要准备一个**公开 GitHub 仓库**作为图片资源仓库，例如：

```text
yourname/blog-assets
```

仓库必须公开，否则 jsDelivr 无法访问图片。

本机还需要能通过 Git 推送到这个仓库。也就是说，你需要已经配置好 GitHub 登录凭据、SSH key 或 HTTPS token。

## Codex 中的典型用法

如果你已经安装了这个 Skill，可以直接对 Codex 说：

```text
把 /path/to/article.md 输出为支持 CSDN 的博客，图片仓库用 yourname/blog-assets
```

如果没有指定仓库，Codex 会要求你提供一个公开 GitHub 仓库地址，例如：

```text
https://github.com/yourname/blog-assets
```

## 命令行用法

Skill 内置脚本：

```bash
python3 scripts/publish_markdown.py \
  --input "/path/to/article.md" \
  --repo "yourname/blog-assets" \
  --check-links
```

运行成功后会生成：

```text
article（平台发布版）.md
article（平台发布版）.image-map.json
article（平台发布版）.publish-report.json
```

## 参数说明

```bash
--input
```

输入 Markdown 文件路径。

```bash
--repo
```

公开 GitHub 图片仓库，支持以下格式：

```text
owner/repo
https://github.com/owner/repo
https://github.com/owner/repo.git
```

```bash
--output
```

指定输出 Markdown 文件。不填时默认输出：

```text
<原文件名>（平台发布版）.md
```

```bash
--slug
```

指定图片在仓库中的文章目录名。不填时根据 Markdown 文件名自动生成。

```bash
--check-links
```

上传后抽查生成的 jsDelivr 图片链接是否可访问。

```bash
--dry-run
```

只测试扫描和回写逻辑，不克隆仓库、不提交、不推送。

## 输出示例

原始 Markdown：

```md
![安装 PPT Skill](image%205.png)
```

转换后：

```md
![安装 PPT Skill](https://cdn.jsdelivr.net/gh/yourname/blog-assets@2696885/articles/codex-ppt-skill/06-install-ppt-skill.png)
```

## 安装方式

可以让 Codex 使用 `skill-installer` 从 GitHub 安装：

```text
帮我安装 https://github.com/STRUGGLE1999/markdown-platform-publisher-skill 这个 Skill
```

安装后重启 Codex，让新 Skill 生效。

## 注意事项

- GitHub 仓库必须公开。
- 图片会被上传到 GitHub，不能放隐私或敏感截图。
- jsDelivr 偶尔会有短暂缓存延迟，刚推送后可能需要等一会儿。
- 如果 Git push 失败，请检查 GitHub 权限、本机凭据和仓库地址。
- 这个 Skill 只生成平台发布版 Markdown，不会自动替你发布到 CSDN 或其他平台，除非你另外明确要求。

## 目录结构

```text
markdown-platform-publisher/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── scripts/
    └── publish_markdown.py
```

