"""load() and validate(): the SHACL conventions both ontologies follow.

Data is validated with the ontology merged into the data graph, so class and
scheme checks can see the vocabulary. No inference: what is not stated is not
assumed (metawork-ontology ADR-0002). ``advanced=True`` turns on SHACL-SPARQL,
which both ontologies' shapes use (ADR-0005, decision 5).
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib import Graph


def _parse_all(paths: Iterable[Path]) -> Graph:
    g = Graph()
    for f in paths:
        g.parse(f, format="turtle")
    return g


def load(ontology: Path, shapes: Path | Iterable[Path]) -> tuple[Graph, Graph]:
    """Read the ontology and the shapes. ``shapes`` is one file, a directory of ``*.ttl``, or a list of files."""
    if isinstance(shapes, Path):
        shapes = sorted(shapes.glob("*.ttl")) if shapes.is_dir() else [shapes]
    shapes = list(shapes)
    if not shapes:
        raise FileNotFoundError("no shapes files given")
    return _parse_all([ontology]), _parse_all(shapes)


def validate(data: Graph, ont: Graph, shapes: Graph) -> tuple[bool, Graph, str]:
    """Run SHACL over ``data + ont``. Returns (conforms, report_graph, report_text)."""
    return shacl_validate(data + ont, shacl_graph=shapes, inference="none", advanced=True, abort_on_first=False)


def validate_files(files: Iterable[Path], ont: Graph, shapes: Graph) -> tuple[bool, Graph, str]:
    """Merge Turtle ``files`` into one data graph and validate it."""
    return validate(_parse_all(files), ont, shapes)
