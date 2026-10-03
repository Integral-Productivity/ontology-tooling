"""The IRI-to-file check and the hub rules, as functions.

Replaces the inline Python each ontology repository carried in pages.yml
(metawork-ontology ADR-0005, decision 1). ontology-hub's Worker serves
``https://<host><path>`` from the project site at the same ``<path>`` for a
registered prefix ``/<name>/`` and its Turtle file ``/<name>.ttl``
(ontology-hub ADR-0002), so every minted IRI needs a file at its own path.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF


class HubRuleError(Exception):
    """The built site breaks a rule of the ontology hub. The build must fail."""


def _base(g: Graph) -> str:
    ontos = list(g.subjects(RDF.type, OWL.Ontology))
    if len(ontos) != 1:
        raise ValueError(f"expected one owl:Ontology, got {len(ontos)}: {ontos}")
    return str(ontos[0]).rstrip("/")


def missing_iris(g: Graph, site_dir: Path) -> list[str]:
    """Every subject IRI on the ontology's host that has no ``index.html`` at its path under ``site_dir``.

    An IRI on the same host but outside the ontology's prefix counts as missing:
    the hub routes only ``/<name>/`` to this repository.
    """
    base = _base(g)
    url = urlparse(base)
    origin, prefix = f"{url.scheme}://{url.netloc}", url.path.rstrip("/") + "/"
    missing = []
    for s in sorted({str(x) for x in g.subjects() if isinstance(x, URIRef)}):
        if not s.startswith(origin + "/"):
            continue
        path = s[len(origin):].split("#")[0]
        if path == prefix.rstrip("/"):
            path = prefix
        if not path.startswith(prefix) or not (site_dir / path.strip("/") / "index.html").is_file():
            missing.append(s)
    return missing


def hub_rule_violations(site_dir: Path, name: str) -> list[str]:
    """The hub rules (ontology-hub ADR-0002) the site breaks, as messages. Empty when it keeps them all."""
    out = []
    if not (site_dir / f"{name}.ttl").is_file():
        out.append(f"/{name}.ttl is missing: the Turtle file must sit at the root of the site")
    if (site_dir / name / f"{name}.ttl").exists():
        out.append(f"/{name}/{name}.ttl exists: the Turtle file belongs at /{name}.ttl, not under the prefix")
    if (site_dir / "CNAME").exists():
        out.append("site/CNAME exists: a project site must not carry a custom domain (the hub owns it)")
    if not (site_dir / ".nojekyll").is_file():
        out.append(".nojekyll is missing: GitHub Pages would run Jekyll over the site")
    if not (site_dir / name / "index.html").is_file():
        out.append(f"/{name}/index.html is missing: the ontology IRI must resolve")
    return out


def check_site(ttl: Path, site_dir: Path) -> list[str]:
    """All problems with a built site: hub-rule violations, then IRIs without a page."""
    g = Graph().parse(ttl, format="turtle")
    name = urlparse(_base(g)).path.strip("/")
    problems = hub_rule_violations(site_dir, name)
    problems += [f"no page for {iri}" for iri in missing_iris(g, site_dir)]
    return problems
