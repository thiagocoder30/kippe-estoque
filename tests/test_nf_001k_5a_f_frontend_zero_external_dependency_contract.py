from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"


REMOTE_URL = re.compile(
    r"""^(?:https?:)?//""",
    re.IGNORECASE,
)


def _is_remote(value: str) -> bool:
    return bool(
        REMOTE_URL.match(
            value.strip()
        )
    )


def _read(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def test_web_tree_exists():
    assert WEB_ROOT.is_dir()


def test_index_loads_no_remote_runtime_resources():
    index = WEB_ROOT / "index.html"

    assert index.is_file()

    source = _read(index)

    attributes = re.findall(
        r"""
        \b
        (?:src|href)
        \s*=\s*
        ["']
        ([^"']+)
        ["']
        """,
        source,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    remote = [
        value
        for value in attributes
        if _is_remote(value)
    ]

    assert remote == []

    assert (
        "/css/generated/"
        "tailwind.min.css"
        in source
    )

    assert (
        "/vendor/"
        "html5-qrcode-2.3.8.min.js"
        in source
    )


def test_manifest_contains_only_local_icons():
    path = WEB_ROOT / "manifest.json"

    assert path.is_file()

    manifest = json.loads(
        _read(path)
    )

    icons = manifest.get(
        "icons",
        [],
    )

    assert icons

    for icon in icons:
        src = icon.get(
            "src",
            "",
        )

        assert src
        assert not _is_remote(src)

        local_path = (
            WEB_ROOT
            / src.lstrip("/")
        )

        assert local_path.is_file()


def test_css_has_no_remote_runtime_imports():
    css_files = sorted(
        path
        for path in WEB_ROOT.rglob("*.css")
        if path.is_file()
    )

    violations = []

    patterns = [
        re.compile(
            r"""
            @import
            \s+
            (?:url\()?
            \s*
            ["']?
            ((?:https?:)?//[^"')\s;]+)
            """,
            re.IGNORECASE
            | re.VERBOSE,
        ),
        re.compile(
            r"""
            url\(
            \s*
            ["']?
            ((?:https?:)?//[^"')\s]+)
            """,
            re.IGNORECASE
            | re.VERBOSE,
        ),
    ]

    for path in css_files:
        source = _read(path)

        for pattern in patterns:
            for match in pattern.finditer(
                source
            ):
                violations.append(
                    (
                        path.relative_to(
                            PROJECT_ROOT
                        ).as_posix(),
                        match.group(1),
                    )
                )

    assert violations == []


def test_kippe_owned_javascript_contains_no_remote_network_targets():
    js_files = sorted(
        path
        for path in (
            WEB_ROOT / "js"
        ).rglob("*.js")
        if path.is_file()
    )

    violations = []

    absolute_url = re.compile(
        r"""
        ["']
        ((?:https?:)?//
        [^"']+)
        ["']
        """,
        re.IGNORECASE
        | re.VERBOSE,
    )

    for path in js_files:
        source = _read(path)

        for match in absolute_url.finditer(
            source
        ):
            violations.append(
                (
                    path.relative_to(
                        PROJECT_ROOT
                    ).as_posix(),
                    match.group(1),
                )
            )

    assert violations == []


def test_api_client_remains_same_origin():
    api_file = WEB_ROOT / "js" / "api.js"

    assert api_file.is_file()

    source = _read(api_file)

    assert (
        "constructor(baseURL = '')"
        in source
    )

    absolute_api_urls = re.findall(
        r"""https?://[^\s"'<>]+""",
        source,
        flags=re.IGNORECASE,
    )

    assert absolute_api_urls == []


def test_scanner_application_code_has_no_remote_runtime_loader():
    scanner_file = (
        WEB_ROOT
        / "js"
        / "scanner.js"
    )

    assert scanner_file.is_file()

    source = _read(scanner_file)

    assert "https://" not in source.lower()
    assert "http://" not in source.lower()


def test_required_local_runtime_assets_exist():
    required = [
        WEB_ROOT
        / "css"
        / "generated"
        / "tailwind.min.css",

        WEB_ROOT
        / "vendor"
        / "html5-qrcode-2.3.8.min.js",

        WEB_ROOT
        / "icons"
        / "kippe-192.png",

        WEB_ROOT
        / "icons"
        / "kippe-512.png",
    ]

    for path in required:
        assert path.is_file()
        assert path.stat().st_size > 0
