#!/usr/bin/env python3
"""Publish Markdown local images through GitHub + jsDelivr.

The script uploads local Markdown images to a public GitHub repository,
rewrites image references to jsDelivr HTTPS URLs, and validates the result.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_IMG_RE = re.compile(
    r"(<img\b[^>]*?\bsrc\s*=\s*)([\"'])(.*?)(\2)([^>]*>)",
    re.IGNORECASE | re.DOTALL,
)
REMOTE_SCHEMES = {"http", "https", "data", "mailto", "tel"}


@dataclass
class ImageRef:
    kind: str
    raw_url: str
    local_path: Path
    alt: str


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        details = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{details}")
    return result


def slugify(value: str, fallback: str = "article") -> str:
    value = unquote(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or fallback


def parse_repo(value: str) -> tuple[str, str, str]:
    value = value.strip()
    if not value:
        raise ValueError("Repository is required.")
    if value.startswith("git@github.com:"):
        slug = value.removeprefix("git@github.com:").removesuffix(".git")
    elif value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        slug = parsed.path.strip("/").removesuffix(".git")
    else:
        slug = value.removesuffix(".git").strip("/")
    parts = slug.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid GitHub repo: {value!r}. Use owner/repo or a GitHub URL.")
    owner, repo = parts
    clone_url = f"https://github.com/{owner}/{repo}.git"
    return owner, repo, clone_url


def is_remote(url: str) -> bool:
    if url.startswith("//"):
        return True
    scheme = urlparse(url).scheme.lower()
    return scheme in REMOTE_SCHEMES


def strip_fragment_and_query(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme:
        return url
    return parsed.path


def resolve_local_url(markdown_path: Path, raw_url: str) -> Path:
    path_part = strip_fragment_and_query(raw_url)
    decoded = unquote(path_part)
    path = Path(decoded)
    if not path.is_absolute():
        path = markdown_path.parent / path
    return path.resolve()


def collect_refs(markdown_path: Path, text: str) -> list[ImageRef]:
    refs: list[ImageRef] = []
    for match in MD_IMAGE_RE.finditer(text):
        alt, raw_url = match.group(1), match.group(2)
        if not is_remote(raw_url):
            refs.append(ImageRef("markdown", raw_url, resolve_local_url(markdown_path, raw_url), alt))
    for match in HTML_IMG_RE.finditer(text):
        raw_url = match.group(3)
        if not is_remote(raw_url):
            refs.append(ImageRef("html", raw_url, resolve_local_url(markdown_path, raw_url), "image"))
    return refs


def unique_local_refs(refs: Iterable[ImageRef]) -> list[ImageRef]:
    seen: set[Path] = set()
    unique: list[ImageRef] = []
    for ref in refs:
        if ref.local_path not in seen:
            seen.add(ref.local_path)
            unique.append(ref)
    return unique


def asset_name(index: int, ref: ImageRef) -> str:
    ext = ref.local_path.suffix.lower() or ".png"
    label_source = ref.alt or ref.local_path.stem
    label = slugify(label_source, fallback=slugify(ref.local_path.stem, "image"))
    return f"{index:02d}-{label}{ext}"


def clone_or_init_repo(clone_url: str, branch: str, work_root: Path) -> Path:
    repo_dir = work_root / "repo"
    result = run(["git", "clone", clone_url, str(repo_dir)], check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    if not (repo_dir / ".git").exists():
        raise RuntimeError("Git clone did not create a repository.")
    branch_result = run(["git", "branch", "--show-current"], cwd=repo_dir, check=False)
    current = branch_result.stdout.strip()
    if not current:
        run(["git", "checkout", "-B", branch], cwd=repo_dir)
    elif current != branch:
        run(["git", "checkout", "-B", branch], cwd=repo_dir)
    return repo_dir


def ensure_git_identity(repo_dir: Path) -> None:
    name = run(["git", "config", "user.name"], cwd=repo_dir, check=False).stdout.strip()
    email = run(["git", "config", "user.email"], cwd=repo_dir, check=False).stdout.strip()
    if not name:
        run(["git", "config", "user.name", "Codex Publisher"], cwd=repo_dir)
    if not email:
        run(["git", "config", "user.email", "codex-publisher@example.local"], cwd=repo_dir)


def copy_assets(unique_refs: list[ImageRef], repo_dir: Path, asset_prefix: str) -> dict[str, str]:
    dest_dir = repo_dir / asset_prefix
    dest_dir.mkdir(parents=True, exist_ok=True)
    local_to_asset: dict[str, str] = {}
    used: set[str] = set()
    for index, ref in enumerate(unique_refs, start=1):
        name = asset_name(index, ref)
        if name in used:
            stem, ext = os.path.splitext(name)
            name = f"{stem}-{index}{ext}"
        used.add(name)
        dest = dest_dir / name
        shutil.copy2(ref.local_path, dest)
        local_to_asset[str(ref.local_path)] = f"{asset_prefix}/{name}"
    return local_to_asset


def rewrite_markdown(text: str, refs: list[ImageRef], local_to_url: dict[str, str]) -> str:
    raw_to_url: dict[str, str] = {}
    for ref in refs:
        raw_to_url[ref.raw_url] = local_to_url[str(ref.local_path)]

    def replace_md(match: re.Match[str]) -> str:
        alt, raw_url = match.group(1), match.group(2)
        if raw_url not in raw_to_url:
            return match.group(0)
        return f"![{alt}]({raw_to_url[raw_url]})"

    def replace_html(match: re.Match[str]) -> str:
        prefix, quote, raw_url, _quote2, suffix = match.groups()
        if raw_url not in raw_to_url:
            return match.group(0)
        return f"{prefix}{quote}{raw_to_url[raw_url]}{quote}{suffix}"

    text = MD_IMAGE_RE.sub(replace_md, text)
    text = HTML_IMG_RE.sub(replace_html, text)
    return text


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}（平台发布版）{input_path.suffix}")


def check_urls(urls: Iterable[str], timeout: float) -> dict[str, int | str]:
    results: dict[str, int | str] = {}
    for url in urls:
        try:
            req = Request(url, method="HEAD", headers={"User-Agent": "Codex Markdown Publisher"})
            with urlopen(req, timeout=timeout) as response:
                results[url] = response.status
        except Exception as exc:  # noqa: BLE001 - report diagnostics to user
            results[url] = f"ERROR: {exc}"
    return results


def validate_output(text: str, original_local_count: int, cdn_base: str) -> dict[str, int]:
    cdn_count = text.count(cdn_base)
    local_markdown_count = 0
    for match in MD_IMAGE_RE.finditer(text):
        if not is_remote(match.group(2)):
            local_markdown_count += 1
    for match in HTML_IMG_RE.finditer(text):
        if not is_remote(match.group(3)):
            local_markdown_count += 1
    return {
        "original_local_image_refs": original_local_count,
        "rewritten_cdn_refs": cdn_count,
        "remaining_local_image_refs": local_markdown_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Markdown local images via GitHub + jsDelivr.")
    parser.add_argument("--input", required=True, help="Input Markdown file.")
    parser.add_argument("--repo", default=os.environ.get("MARKDOWN_PUBLISHER_GITHUB_REPO", "STRUGGLE1999/blog-assets"), help="GitHub repo as owner/repo or URL.")
    parser.add_argument("--output", help="Output Markdown path. Defaults to <name>（平台发布版）.md")
    parser.add_argument("--branch", default="main", help="Branch to push to. Default: main.")
    parser.add_argument("--slug", help="Article slug for asset folder. Defaults to input filename slug.")
    parser.add_argument("--asset-root", default="articles", help="Root folder in repo. Default: articles.")
    parser.add_argument("--message", help="Git commit message.")
    parser.add_argument("--check-links", action="store_true", help="Check generated jsDelivr links with HTTP HEAD.")
    parser.add_argument("--dry-run", action="store_true", help="Do not clone, commit, or push; rewrite links with a DRYRUN ref for parser testing.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout for --check-links.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input Markdown not found: {input_path}")
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(input_path)
    slug = slugify(args.slug or input_path.stem)
    asset_prefix = f"{args.asset_root.strip('/')}/{slug}"

    text = input_path.read_text(encoding="utf-8")
    refs = collect_refs(input_path, text)
    missing = [str(ref.local_path) for ref in refs if not ref.local_path.exists()]
    if missing:
        print(json.dumps({"error": "missing_local_images", "missing": missing}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    if not refs:
        output_path.write_text(text, encoding="utf-8")
        print(json.dumps({"output": str(output_path), "local_images": 0}, ensure_ascii=False, indent=2))
        return 0

    owner, repo_name, clone_url = parse_repo(args.repo)
    unique_refs = unique_local_refs(refs)

    if args.dry_run:
        with tempfile.TemporaryDirectory(prefix="markdown-platform-publisher-dryrun-") as tmp:
            repo_dir = Path(tmp) / "repo"
            repo_dir.mkdir()
            local_to_asset = copy_assets(unique_refs, repo_dir, asset_prefix)
        commit = "DRYRUN"
    else:
        with tempfile.TemporaryDirectory(prefix="markdown-platform-publisher-") as tmp:
            repo_dir = clone_or_init_repo(clone_url, args.branch, Path(tmp))
            ensure_git_identity(repo_dir)
            local_to_asset = copy_assets(unique_refs, repo_dir, asset_prefix)
            run(["git", "add", asset_prefix], cwd=repo_dir)
            status = run(["git", "status", "--short"], cwd=repo_dir).stdout.strip()
            if status:
                message = args.message or f"Add assets for {slug}"
                run(["git", "commit", "-m", message], cwd=repo_dir)
                run(["git", "push", "origin", args.branch], cwd=repo_dir)
            commit = run(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()

    cdn_base = f"https://cdn.jsdelivr.net/gh/{owner}/{repo_name}@{commit}"
    local_to_url = {
        local: f"{cdn_base}/{asset_path}"
        for local, asset_path in local_to_asset.items()
    }
    output_text = rewrite_markdown(text, refs, local_to_url)
    output_path.write_text(output_text, encoding="utf-8")

    mapping = {
        ref.raw_url: {
            "local_path": str(ref.local_path),
            "cdn_url": local_to_url[str(ref.local_path)],
        }
        for ref in refs
    }
    map_path = output_path.with_suffix(".image-map.json")
    report_path = output_path.with_suffix(".publish-report.json")
    map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    validation = validate_output(output_text, len(refs), cdn_base)
    urls = sorted({item["cdn_url"] for item in mapping.values()})
    link_checks = check_urls(urls, args.timeout) if args.check_links and not args.dry_run else {}
    report = {
        "input": str(input_path),
        "output": str(output_path),
        "repo": f"{owner}/{repo_name}",
        "branch": args.branch,
        "commit": commit,
        "dry_run": args.dry_run,
        "asset_prefix": asset_prefix,
        "unique_assets": len(unique_refs),
        "validation": validation,
        "link_checks": link_checks,
        "image_map": str(map_path),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if validation["remaining_local_image_refs"] != 0:
        return 3
    if validation["rewritten_cdn_refs"] != len(refs):
        return 4
    if link_checks and any(value != 200 for value in link_checks.values()):
        return 5
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - CLI error surface
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
