from __future__ import annotations

import argparse
import functools
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import nox

os.environ["PDM_IGNORE_SAVED_PYTHON"] = "1"

CI = os.environ.get("CI") is not None

ROOT = Path(".")
MAIN_BRANCH_NAME = "master"
PYTHON_VERSIONS = ["3.9", "3.11", "3.12"]
PYTHON_DEFAULT_VERSION = PYTHON_VERSIONS[-1]

DJANGO_VERSIONS = ["3.2", "4.2"]
DEMO_APP_DIR = ROOT / "demo"

nox.options.default_venv_backend = "venv"
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True


# In CI, use Python interpreter provided by GitHub Actions
if CI:
    PYTHON_VERSIONS = [sys.executable]


def install(session: nox.Session, *args, no_self=False, no_default=False):
    other_args = []
    if no_self:
        other_args.append("--no-self")
    if no_default:
        other_args.append("--no-default")
    for group in args:
        other_args.extend(["--group", group])
    session.run("pdm", "install", "--check", *other_args, external=True)


@functools.lru_cache
def _list_files() -> list[Path]:
    file_list = []
    for cmd in (
        ["git", "ls-files"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        cmd_result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        file_list.extend(cmd_result.stdout.splitlines())
    file_paths = [Path(p) for p in file_list]
    return file_paths


def list_files(suffix: str | None = None) -> list[Path]:
    """List all non-files not-ignored by git."""
    file_paths = _list_files()
    if suffix is not None:
        file_paths = [p for p in file_paths if p.suffix == suffix]
    return file_paths


def run_readable(session, mode="check"):
    session.run(
        "docker",
        "run",
        "--platform",
        "linux/amd64",
        "--rm",
        "-v",
        f"{ROOT.absolute()}:/data",
        "-w",
        "/data",
        "ghcr.io/bobheadxi/readable:v0.5.0@sha256:423c133e7e9ca0ac20b0ab298bd5dbfa3df09b515b34cbfbbe8944310cc8d9c9",
        mode,
        "![.]**/*.md",
        external=True,
    )


def run_shellcheck(session, mode="check"):
    shellcheck_cmd = [
        "docker",
        "run",
        "--platform",
        "linux/amd64",  # while this image is multi-arch, we cannot use digest with multi-arch images
        "--rm",
        "-v",
        f"{ROOT.absolute()}:/mnt",
        "-w",
        "/mnt",
        "-q",
        "koalaman/shellcheck:0.9.0@sha256:a527e2077f11f28c1c1ad1dc784b5bc966baeb3e34ef304a0ffa72699b01ad9c",
    ]

    files = list_files(suffix=".sh")
    if not files:
        session.log("No shell files found")
        return
    shellcheck_cmd.extend(files)

    if mode == "fmt":
        with tempfile.NamedTemporaryFile(mode="w+") as diff_file:
            session.run(
                *shellcheck_cmd,
                "--format=diff",
                external=True,
                stdout=diff_file,
                success_codes=[0, 1],
            )
            diff_file.seek(0)
            diff = diff_file.read()
            if len(diff.splitlines()) > 1:  # ignore single-line message
                session.log("Applying shellcheck patch:\n%s", diff)
                subprocess.run(
                    ["patch", "-p1"],
                    input=diff,
                    text=True,
                    check=True,
                )

    session.run(*shellcheck_cmd, external=True)


@nox.session(name="format", python=PYTHON_DEFAULT_VERSION, tags=["format", "check"])
def format_(session):
    """Lint the code and apply fixes in-place whenever possible."""
    install(session, "lint", no_self=True, no_default=True)
    session.run("ruff", "check", "--fix", ".")
    run_shellcheck(session, mode="fmt")
    run_readable(session, mode="fmt")
    session.run("ruff", "format", ".")


@nox.session(python=PYTHON_DEFAULT_VERSION, tags=["lint", "check"])
def lint(session):
    """Run linters in readonly mode."""
    install(session, "lint")
    session.run("ruff", "check", "--diff", "--unsafe-fixes", ".")
    session.run("ruff", "format", "--diff", ".")
    session.run("mypy", ".")
    session.run("codespell", ".")
    run_shellcheck(session, mode="check")
    run_readable(session, mode="check")


@nox.session(python=PYTHON_VERSIONS, tags=["test", "check"])
@nox.parametrize("django", DJANGO_VERSIONS)
def test(session, django: str):
    session.run("pdm", "install", "--dev")
    session.run("pip", "install", f"django~={django}.0")
    session.run("pytest", "-vv", "-n", "auto", *session.posargs)


@nox.session(python=PYTHON_DEFAULT_VERSION)
def make_release(session):
    parser = argparse.ArgumentParser()

    def version(value):
        if not re.match(r"\d+\.\d+\.\d+", value):
            raise argparse.ArgumentTypeError("Invalid version format")
        return value

    parser.add_argument(
        "release_version",
        help="Release version in semver format (e.g. 1.2.3)",
        type=version,
    )
    parsed_args = parser.parse_args(session.posargs)

    local_changes = subprocess.check_output(["git", "diff", "--stat"])
    if local_changes:
        session.error("Uncommitted changes detected")

    current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True)
    if current_branch != MAIN_BRANCH_NAME:
        session.error(f"WARNING: releasing from a branch different than {MAIN_BRANCH_NAME!r}")

    session.run("towncrier", "build", "--yes", "--version", parsed_args.release_version)
