"""Build an ontology's static project site for GitHub Pages.

Output layout, for an ontology whose IRI is ``https://<host>/<name>``:

  site/
  ├── .nojekyll
  ├── index.html                project-site root: link to /<name>/ (not served on the domain)
  ├── <name>.ttl                the machine-readable file, at the root (hub rule)
  └── <name>/
      ├── index.html            the ontology page: schemes, schema terms (<base>#X) as #anchors
      ├── <path>/index.html     one page per subject IRI minted under <base>/
      └── v/<version>/          dated snapshot (metawork-ontology ADR-0004 decision 3):
                                index.html and <name>.ttl, one per release tag vX.Y.Z
                                (the file as it was at that tag) plus the current version

A released version's file may not change: if the current owl:versionInfo names
a release tag and the file differs from it, the build fails with ReleaseError
until the version is bumped. Snapshot rules ported from
vertical-development-ontology#6 (its PR #12). They need the full git history,
so check out with fetch-depth: 0.

The hub rules are checked at the end and a broken rule raises HubRuleError,
so a renderer hook cannot ship a site the hub would serve wrongly.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from rdflib import Graph

from .check import HubRuleError, hub_rule_violations
from .site import Site

RELEASE_TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")


class ReleaseError(Exception):
    """A release tag and its ontology file disagree, or a released file was changed. The build must fail."""


def find_ontology(root: Path) -> Path:
    """The one Turtle file in ``<root>/ontology/``."""
    files = sorted((root / "ontology").glob("*.ttl"))
    if len(files) != 1:
        raise FileNotFoundError(f"expected one ontology/*.ttl under {root}, found {[f.name for f in files]}")
    return files[0]


def _git(cwd: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, check=True).stdout


def released(ttl: Path) -> dict[str, bytes]:
    """The ontology file at each release tag vX.Y.Z, keyed by version; {} outside a git work tree."""
    try:
        top = Path(_git(ttl.parent, "rev-parse", "--show-toplevel").decode().strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    rel = ttl.resolve().relative_to(top.resolve()).as_posix()
    by_version = {}
    for tag in _git(top, "tag", "--list").decode().split():
        if not (m := RELEASE_TAG.match(tag)):
            continue
        version = m.group(1)
        try:
            data = _git(top, "show", f"{tag}:{rel}")
        except subprocess.CalledProcessError:
            raise ReleaseError(f"release tag {tag}: {rel} does not exist at that tag") from None
        found = Site(Graph().parse(data=data, format="turtle")).version
        if found != version:
            raise ReleaseError(f"release tag {tag}: {rel} has owl:versionInfo {found}, not {version}")
        by_version[version] = data
    return by_version


def snapshots(site: Site, ttl: Path, releases: dict[str, bytes] | None = None) -> dict[str, bytes]:
    """Versions to publish under ``/<name>/v/<version>/``: every release plus the current version.

    Raises ReleaseError when the current version is released and the file differs from the tag.
    """
    if releases is None:
        releases = released(ttl)
    data = ttl.read_bytes()
    if site.version in releases and releases[site.version] != data:
        raise ReleaseError(f"{ttl.name} differs from the released tag v{site.version}: "
                           f"bump owl:versionInfo before changing a released version")
    return dict(sorted({site.version: data, **releases}.items()))


def build(out: Path, ttl: Path, site_cls: type[Site] = Site, releases: dict[str, bytes] | None = None) -> Site:
    """Render ``ttl`` into ``out`` (replaced if it exists). Returns the Site.

    ``releases`` defaults to the git release tags (see ``released``). Raises
    ReleaseError before writing anything, and HubRuleError after.
    """
    site = site_cls(Graph().parse(ttl, format="turtle"))
    versions = snapshots(site, ttl, releases)
    if out.exists():
        shutil.rmtree(out)
    top = out / site.name
    top.mkdir(parents=True)
    (out / ".nojekyll").write_text("")
    (out / "index.html").write_text(site.root_page(), encoding="utf-8")
    shutil.copy(ttl, out / f"{site.name}.ttl")
    (top / "index.html").write_text(site.ontology_page(), encoding="utf-8")

    # snapshots() makes the released file for site.version, when present, equal to ttl.
    for version, data in versions.items():
        snap_site = site if version == site.version else site_cls(Graph().parse(data=data, format="turtle"))
        snap = out / snap_site.name / "v" / version
        snap.mkdir(parents=True)
        (snap / "index.html").write_text(snap_site.ontology_page(snapshot=True), encoding="utf-8")
        (snap / f"{snap_site.name}.ttl").write_bytes(data)

    for s in site.page_subjects():
        d = out / site.path(s).strip("/")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(site.render(s), encoding="utf-8")

    if problems := hub_rule_violations(out, site.name):
        raise HubRuleError("; ".join(problems))
    return site
