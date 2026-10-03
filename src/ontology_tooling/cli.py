"""Command line: ``ontology-tooling build | check-iris | validate``.

Run from an ontology repository's root. The ontology defaults to the one
``ontology/*.ttl`` file, the shapes to ``shapes/*.ttl``.

  ontology-tooling build [--out site] [--site-class tools.site_hooks:MySite] [--no-release-snapshots]
  ontology-tooling check-iris [--site site]
  ontology-tooling validate examples/a.ttl [examples/b.ttl ...]   # inputs are merged

Exit status: 0 ok; 1 the check failed (missing pages, hub rule broken, SHACL result); 2 usage.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from . import __version__
from .build import ReleaseError, build, find_ontology
from .check import HubRuleError, check_site
from .shacl import load, validate_files
from .site import Site


def _site_class(spec: str | None) -> type[Site]:
    if not spec:
        return Site
    module, _, attr = spec.partition(":")
    if not attr:
        raise SystemExit(f"--site-class must be module:Class, got {spec!r}")
    sys.path[:0] = [str(Path.cwd()), str(Path.cwd() / "tools")]
    cls = getattr(importlib.import_module(module), attr)
    if not (isinstance(cls, type) and issubclass(cls, Site)):
        raise SystemExit(f"{spec} is not a subclass of ontology_tooling.Site")
    return cls


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ontology-tooling", description=__doc__.split("\n")[0])
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--ontology", type=Path, help="Turtle file (default: the one ontology/*.ttl)")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="render the static site")
    b.add_argument("--out", type=Path, default=Path("site"))
    b.add_argument("--site-class", help="module:Class, a Site subclass with renderer hooks")
    b.add_argument("--no-release-snapshots", action="store_true",
                   help="ignore git release tags; snapshot the current version only (for repos whose tags are not ontology releases)")
    c = sub.add_parser("check-iris", help="every minted IRI has a page; the hub rules hold")
    c.add_argument("--site", type=Path, default=Path("site"))
    v = sub.add_parser("validate", help="SHACL-validate data files (merged) against the ontology and shapes")
    v.add_argument("--shapes", type=Path, nargs="+", default=[Path("shapes")])
    v.add_argument("data", type=Path, nargs="+")
    a = p.parse_args(argv)

    ttl = a.ontology or find_ontology(Path.cwd())
    if a.cmd == "build":
        try:
            site = build(a.out, ttl, _site_class(a.site_class), releases={} if a.no_release_snapshots else None)
        except HubRuleError as err:
            print(f"hub rule broken: {err}", file=sys.stderr)
            return 1
        except ReleaseError as err:
            print(f"release check failed: {err}", file=sys.stderr)
            return 1
        print(f"built {a.out}: /{site.name}/ version {site.version}, {len(site.page_subjects())} IRI pages")
        return 0
    if a.cmd == "check-iris":
        problems = check_site(ttl, a.site)
        for msg in problems:
            print(msg, file=sys.stderr)
        if problems:
            return 1
        print(f"every minted IRI in {ttl} resolves to a file under {a.site}")
        return 0
    shapes = a.shapes[0] if len(a.shapes) == 1 else a.shapes
    ont, sh = load(ttl, shapes)
    conforms, _, text = validate_files(a.data, ont, sh)
    print(text)
    return 0 if conforms else 1


if __name__ == "__main__":
    sys.exit(main())
