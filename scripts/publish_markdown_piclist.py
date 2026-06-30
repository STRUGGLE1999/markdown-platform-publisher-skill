#!/usr/bin/env python3
"""Upload local Markdown images through PicList and rewrite image URLs."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\n]+)\)")
HTML_IMAGE_RE = re.compile(
    r"(<img\b[^>]*?\bsrc=[\"'])([^\"']+)([\"'][^>]*>)",
    re.IGNORECASE,
)
FENCED_CODE_RE = re.compile(r"(^|\n)(`{3,}|~{3,})[^\n]*\n.*?\n\2(?=\n|$)", re.DOTALL)
IMAGE_EXTS = {".apng", ".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
DEFAULT_ASSET_ROOT = "articles"
CHINESE_SLUG_TERMS = [
    ("多平台", "multi-platform"),
    ("全平台", "multi-platform"),
    ("文案创作", "copywriting"),
    ("文案", "copywriting"),
    ("创作", "creation"),
    ("助手", "assistant"),
    ("工作流", "workflow"),
    ("博客", "blog"),
    ("教程", "tutorial"),
    ("指南", "guide"),
    ("知识工作者", "knowledge-worker"),
    ("使用", "usage"),
    ("搭建", "build"),
    ("测试", "test"),
    ("封面", "cover"),
]


@dataclass(frozen=True)
class ImageRef:
    kind: str
    raw: str
    url: str
    local_path: Path
    alt: str = ""


def is_remote(url: str) -> bool:
    lower = url.lower()
    return lower.startswith(("http://", "https://", "data:", "//", "mailto:"))


def slugify(value: str, fallback: str = "article") -> str:
    value = value.strip().lower()
    for cn, en in CHINESE_SLUG_TERMS:
        value = value.replace(cn.lower(), f" {en} ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or fallback


def normalize_prefix(value: str) -> str:
    value = value.replace("\\", "/").strip("/")
    return f"{value}/" if value else ""


def default_piclist_config_path() -> Path:
    candidates: list[Path] = []

    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "piclist" / "data.json")

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        candidates.append(Path(xdg_config_home) / "piclist" / "data.json")

    home = Path.home()
    candidates.extend(
        [
            home / "Library" / "Application Support" / "piclist" / "data.json",
            home / ".config" / "piclist" / "data.json",
            home / "AppData" / "Roaming" / "piclist" / "data.json",
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def strip_wrapping(url: str) -> str:
    url = url.strip()
    if url.startswith("<") and url.endswith(">"):
        return url[1:-1].strip()
    return url


def is_inside_ranges(position: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def is_placeholder(url: str) -> bool:
    value = strip_wrapping(url).strip()
    if not value:
        return True
    if value.startswith("{{") and value.endswith("}}"):
        return True
    if value in {"图片链接", "image", "url", "link", "TODO", "todo"}:
        return True
    return False


def should_collect_local(md_path: Path, url: str) -> bool:
    if is_remote(url) or is_placeholder(url):
        return False
    path = resolve_local(md_path, url)
    if path.exists():
        return True
    clean = strip_wrapping(url).split("#", 1)[0].split("?", 1)[0]
    suffix = Path(urllib.parse.unquote(clean)).suffix.lower()
    return suffix in IMAGE_EXTS


def resolve_local(md_path: Path, url: str) -> Path:
    clean = strip_wrapping(url).split("#", 1)[0].split("?", 1)[0]
    clean = urllib.parse.unquote(clean)
    path = Path(clean)
    if not path.is_absolute():
        path = md_path.parent / path
    return path.resolve()


def collect_refs(md_path: Path, text: str) -> list[ImageRef]:
    refs: list[ImageRef] = []
    code_ranges = [(match.start(), match.end()) for match in FENCED_CODE_RE.finditer(text)]
    for match in MD_IMAGE_RE.finditer(text):
        if is_inside_ranges(match.start(), code_ranges):
            continue
        raw = match.group(0)
        alt = match.group(1)
        url = strip_wrapping(match.group(2))
        if should_collect_local(md_path, url):
            refs.append(ImageRef("markdown", raw, url, resolve_local(md_path, url), alt))
    for match in HTML_IMAGE_RE.finditer(text):
        if is_inside_ranges(match.start(), code_ranges):
            continue
        raw = match.group(0)
        url = strip_wrapping(match.group(2))
        if should_collect_local(md_path, url):
            refs.append(ImageRef("html", raw, url, resolve_local(md_path, url)))
    return refs


def unique_refs(refs: list[ImageRef]) -> list[ImageRef]:
    seen: set[Path] = set()
    unique: list[ImageRef] = []
    for ref in refs:
        if ref.local_path not in seen:
            seen.add(ref.local_path)
            unique.append(ref)
    return unique


def ascii_name(index: int, ref: ImageRef) -> str:
    source = ref.local_path.stem.lower()
    source = re.sub(r"[^a-z0-9]+", "-", source).strip("-")
    if not source:
        source = "image"
    if "codex" in source:
        source = "codex"
    ext = ref.local_path.suffix.lower() or mimetypes.guess_extension("image/png") or ".png"
    return f"{index:02d}-{source}{ext}"


def upload_one(endpoint: str, image_path: Path, timeout: float) -> str:
    payload = json.dumps({"list": [str(image_path)]}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"PicList upload request failed for {image_path}: {exc}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"PicList returned non-JSON response for {image_path}: {body[:500]}") from exc

    if not data.get("success"):
        raise RuntimeError(f"PicList upload failed for {image_path}: {json.dumps(data, ensure_ascii=False)}")
    result = data.get("result") or []
    if not result or not isinstance(result[0], str):
        raise RuntimeError(f"PicList did not return an image URL for {image_path}: {json.dumps(data, ensure_ascii=False)}")
    return result[0]


def check_url(url: str, timeout: float) -> dict[str, int | str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(16)
            return {
                "status": response.status,
                "content_type": response.headers.get("content-type", ""),
            }
    except Exception as exc:  # noqa: BLE001 - report diagnostics to user
        return {"error": f"{type(exc).__name__}: {exc}"}


class PicListUploadPathOverride:
    def __init__(self, config_path: Path, upload_path: str, enabled: bool = True):
        self.config_path = config_path
        self.upload_path = normalize_prefix(upload_path)
        self.enabled = enabled
        self.original: str | None = None

    def __enter__(self) -> "PicListUploadPathOverride":
        if not self.enabled:
            return self
        if not self.config_path.exists():
            raise FileNotFoundError(f"PicList config not found: {self.config_path}")
        self.original = self.config_path.read_text(encoding="utf-8")
        data = json.loads(self.original)
        current = data.get("picBed", {}).get("current")
        if not current:
            raise RuntimeError("PicList config does not define picBed.current")
        picbed_config = data.get("picBed", {}).get(current)
        if not isinstance(picbed_config, dict) or "uploadPath" not in picbed_config:
            raise RuntimeError(f"PicList current uploader {current!r} does not expose uploadPath")
        picbed_config["uploadPath"] = self.upload_path
        uploader = data.get("uploader", {}).get(current, {})
        default_id = uploader.get("defaultId")
        for item in uploader.get("configList", []):
            if item.get("_id") == default_id:
                item["uploadPath"] = self.upload_path
        self.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.enabled and self.original is not None:
            self.config_path.write_text(self.original, encoding="utf-8")


def rewrite_text(text: str, refs: list[ImageRef], url_map: dict[Path, str]) -> str:
    rewritten = text
    for ref in refs:
        new_url = url_map[ref.local_path]
        if ref.kind == "markdown":
            replacement = f"![{ref.alt}]({new_url})"
            rewritten = rewritten.replace(ref.raw, replacement, 1)
        else:
            replacement = ref.raw.replace(ref.url, new_url, 1)
            rewritten = rewritten.replace(ref.raw, replacement, 1)
    return rewritten


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}（PicList发布版）{input_path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Markdown local images through PicList.")
    parser.add_argument("--input", required=True, help="Input Markdown file.")
    parser.add_argument("--output", help="Output Markdown file. Defaults to <name>（PicList发布版）.md.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:36677/upload", help="PicList upload endpoint.")
    parser.add_argument("--asset-root", default=DEFAULT_ASSET_ROOT, help="Remote root path in PicList image host. Default: articles.")
    parser.add_argument("--slug", help="English article directory name under --asset-root. Defaults to a slug derived from the Markdown filename.")
    parser.add_argument("--piclist-config", default=str(default_piclist_config_path()), help="PicList data.json path used to override uploadPath temporarily.")
    parser.add_argument("--no-set-upload-path", action="store_true", help="Do not modify PicList uploadPath; use the current PicList configured path.")
    parser.add_argument("--expected-url-prefix", help="Expected public image URL prefix, for example https://pub-xxx.r2.dev.")
    parser.add_argument("--check-links", action="store_true", help="Check returned public image URLs after upload.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Upload timeout per image.")
    parser.add_argument("--keep-staged", action="store_true", help="Keep staged ASCII-named upload files next to output.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input Markdown not found: {input_path}")
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(input_path)

    text = input_path.read_text(encoding="utf-8")
    slug = slugify(args.slug or input_path.stem)
    asset_prefix = normalize_prefix(f"{args.asset_root}/{slug}")
    refs = collect_refs(input_path, text)
    missing = [str(ref.local_path) for ref in refs if not ref.local_path.exists()]
    if missing:
        print(json.dumps({"error": "missing_local_images", "missing": missing}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    unique = unique_refs(refs)
    if not unique:
        output_path.write_text(text, encoding="utf-8")
        print(json.dumps({
            "output": str(output_path),
            "local_images": 0,
            "asset_prefix": asset_prefix,
            "slug": slug,
        }, ensure_ascii=False, indent=2))
        return 0

    staged_root = output_path.parent / f"{output_path.stem}.piclist-staged"
    if staged_root.exists():
        shutil.rmtree(staged_root)
    staged_root.mkdir(parents=True)

    url_map: dict[Path, str] = {}
    mapping: dict[str, dict[str, str]] = {}
    try:
        with PicListUploadPathOverride(
            Path(args.piclist_config).expanduser().resolve(),
            asset_prefix,
            enabled=not args.no_set_upload_path,
        ):
            for index, ref in enumerate(unique, start=1):
                staged = staged_root / ascii_name(index, ref)
                shutil.copy2(ref.local_path, staged)
                url = upload_one(args.endpoint, staged, args.timeout)
                if args.expected_url_prefix:
                    expected = args.expected_url_prefix.rstrip("/") + "/"
                    if not url.startswith(expected):
                        raise RuntimeError(f"PicList returned URL outside expected prefix: {url} (expected {expected})")
                url_map[ref.local_path] = url
                mapping[ref.url] = {
                    "local_path": str(ref.local_path),
                    "staged_path": str(staged),
                    "url": url,
                }

        output_text = rewrite_text(text, refs, url_map)
        output_path.write_text(output_text, encoding="utf-8")

        link_checks = {url: check_url(url, args.timeout) for url in url_map.values()} if args.check_links else {}
        map_path = output_path.with_suffix(".image-map.json")
        report_path = output_path.with_suffix(".publish-report.json")
        map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        report = {
            "input": str(input_path),
            "output": str(output_path),
            "endpoint": args.endpoint,
            "asset_prefix": asset_prefix,
            "slug": slug,
            "expected_url_prefix": args.expected_url_prefix,
            "unique_assets": len(unique),
            "validation": {
                "original_local_image_refs": len(refs),
                "rewritten_remote_refs": sum(1 for url in url_map.values() if is_remote(url)),
                "remaining_local_image_refs": len(collect_refs(output_path, output_text)),
            },
            "link_checks": link_checks,
            "image_map": str(map_path),
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        if not args.keep_staged:
            shutil.rmtree(staged_root, ignore_errors=True)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
