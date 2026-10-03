"""Fixtures: read-only copies of real ontologies, built once per module.

- metawork: Integral-Productivity/metawork-ontology at 73b85d8 (ontology, shapes, examples).
- sample: synthetic, with vertical-development-ontology's shape (SKOS-XL labels,
  ordered collection, sources as IRIs). VDO itself is private until its
  publication gate opens, so it is not copied here (#2).
"""
from pathlib import Path

import pytest
from rdflib import Graph

import ontology_tooling as ot

FIXTURES = Path(__file__).parent / "fixtures"
ONTOLOGIES = ["metawork", "sample"]


@pytest.fixture(params=ONTOLOGIES, scope="module")
def repo(request) -> Path:
    return FIXTURES / request.param


@pytest.fixture(scope="module")
def ttl(repo) -> Path:
    return ot.find_ontology(repo)


@pytest.fixture(scope="module")
def graph(ttl) -> Graph:
    return Graph().parse(ttl, format="turtle")


@pytest.fixture(scope="module")
def built(ttl, tmp_path_factory):
    """(site_dir, Site). releases={}: this repository's own tags are not the fixtures' releases."""
    out = tmp_path_factory.mktemp("site")
    return out, ot.build(out, ttl, releases={})
