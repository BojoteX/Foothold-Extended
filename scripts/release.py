#!/usr/bin/env python3
"""Interactive release script for Foothold Extended.

Usage: python scripts/release.py

Walks you through:
1. Shows what's changed since last release
2. Asks for version number
3. Runs tests locally
4. Tags and pushes — GitHub Actions handles the rest
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(cmd: str, capture: bool = True) -> str:
    r = subprocess.run(
        cmd, shell=True, cwd=REPO,
        capture_output=capture, text=True,
    )
    if capture:
        return r.stdout.strip()
    return ""


def run_check(cmd: str) -> int:
    r = subprocess.run(cmd, shell=True, cwd=REPO)
    return r.returncode


def get_last_tag() -> str | None:
    tags = run("git tag --sort=-v:refname")
    if tags:
        return tags.splitlines()[0]
    return None


def get_commits_since(tag: str | None) -> list[str]:
    if tag:
        log = run(f'git log {tag}..HEAD --oneline')
    else:
        log = run('git log --oneline -20')
    return log.splitlines() if log else []


def validate_version(v: str) -> bool:
    return bool(re.match(r'^v\d+\.\d+\.\d+(-\w+)?$', v))


def main():
    # Check clean working tree
    status = run("git status --porcelain")
    if status:
        print("ERROR: Working tree is not clean. Commit or stash changes first.\n")
        print(status)
        sys.exit(1)

    # Check we're on main
    branch = run("git rev-parse --abbrev-ref HEAD")
    if branch != "main":
        print(f"WARNING: You're on '{branch}', not 'main'.")
        resp = input("Continue anyway? (Y/n): ").strip().lower()
        if resp == "n":
            sys.exit(0)

    # Show last release and changes
    last_tag = get_last_tag()
    if last_tag:
        print(f"\nLast release: {last_tag}")
    else:
        print("\nNo previous releases found.")

    commits = get_commits_since(last_tag)
    if not commits:
        print("No new commits since last release. Nothing to release.")
        sys.exit(0)

    print(f"\n{len(commits)} commit(s) since {last_tag or 'beginning'}:\n")
    for c in commits[:15]:
        print(f"  {c}")
    if len(commits) > 15:
        print(f"  ... and {len(commits) - 15} more")

    # Ask for version
    print()
    suggested = "v1.0.0"
    if last_tag:
        m = re.match(r'v(\d+)\.(\d+)\.(\d+)', last_tag)
        if m:
            suggested = f"v{m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}"

    version = input(f"\nVersion to release [{suggested}]: ").strip()
    if not version:
        version = suggested
    if not version.startswith("v"):
        version = f"v{version}"
    if not validate_version(version):
        print(f"Invalid version format: {version}")
        print("Expected: v1.0.0 or v1.0.0-beta")
        sys.exit(1)

    # Check tag doesn't already exist
    existing = run(f"git tag -l {version}")
    if existing:
        print(f"Tag {version} already exists. Choose a different version.")
        sys.exit(1)

    # Run tests
    print("\nRunning tests...")
    rc = run_check(f"{sys.executable} tests/test_briefing.py")
    if rc != 0:
        print("\nTests FAILED. Fix issues before releasing.")
        sys.exit(1)
    print("Tests passed.\n")

    # Confirm
    print(f"Ready to release {version}")
    print(f"  - Tag: {version}")
    print(f"  - Push to: origin/main")
    print(f"  - GitHub Actions will build 8 .miz files + briefing.pyw")
    print(f"  - Release page created automatically\n")

    confirm = input("Proceed? (Y/n): ").strip().lower()
    if confirm == "n":
        print("Aborted.")
        sys.exit(0)

    # Tag and push
    print(f"\nCreating tag {version}...")
    run(f'git tag -a {version} -m "Release {version}"', capture=False)

    print(f"Pushing tag to origin...")
    run(f"git push origin {version}", capture=False)

    print(f"\nDone! Release {version} is being built.")
    print(f"Watch it at: https://github.com/BojoteX/Foothold-Extended/actions")
    print(f"Release page: https://github.com/BojoteX/Foothold-Extended/releases/tag/{version}")


if __name__ == "__main__":
    main()
