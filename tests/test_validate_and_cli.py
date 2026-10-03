"""load()/validate() and the command line, against the fixture ontologies' own examples."""
import os
from pathlib import Path

import pytest
from rdflib import Graph

import ontology_tooling as ot
from ontology_tooling.cli import main

FIXTURES = Path(__file__).parent / "fixtures"

# (fixture, example files merged into one data graph, conforms?)
CASES = [
    ("metawork", ["valid-groups.ttl"], True),
    ("metawork", ["valid-groups.ttl", "valid-decisions.ttl"], True),
    ("metawork", ["invalid-groups.ttl"], False),
    ("metawork", ["valid-groups.ttl", "invalid-decisions.ttl"], False),
    ("sample", ["valid-extension.ttl"], True),
    ("sample", ["invalid-extension.ttl"], False),
]


@pytest.mark.parametrize("name,examples,conforms", CASES)
def test_examples_validate_as_their_repository_says(name, examples, conforms):
    repo = FIXTURES / name
    ont, shapes = ot.load(ot.find_ontology(repo), repo / "shapes")
    ok, _, text = ot.validate_files([repo / "examples" / f for f in examples], ont, shapes)
    assert ok is conforms, text


def test_shacl_sparql_constraints_run():
    repo = FIXTURES / "sample"
    ont, shapes = ot.load(ot.find_ontology(repo), repo / "shapes")
    _, _, text = ot.validate_files([repo / "examples" / "invalid-extension.ttl"], ont, shapes)
    assert "next band must be in the same scheme" in text


def test_no_inference():
    """inference="none": rdfs:domain does not type a node, so a shape on that class does not target it."""
    shapes = Graph().parse(data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        [] a sh:NodeShape ; sh:targetClass <urn:x:C> ; sh:property [ sh:path skos:prefLabel ; sh:minCount 1 ] .""",
        format="turtle")
    ont = Graph().parse(data="""
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        <urn:x:p> rdfs:domain <urn:x:C> .""", format="turtle")
    data = Graph().parse(data='<urn:x:i> <urn:x:p> "v" .', format="turtle")
    ok, _, text = ot.validate(data, ont, shapes)
    assert ok, text


def test_load_accepts_a_file_a_directory_or_a_list():
    repo = FIXTURES / "metawork"
    ttl = ot.find_ontology(repo)
    files = sorted((repo / "shapes").glob("*.ttl"))
    assert len(ot.load(ttl, repo / "shapes")[1]) == len(ot.load(ttl, files)[1])
    assert len(ot.load(ttl, files[0])[1]) < len(ot.load(ttl, files)[1])
    with pytest.raises(FileNotFoundError):
        ot.load(ttl, [])


@pytest.fixture
def in_repo(request):
    def enter(name):
        old = os.getcwd()
        os.chdir(FIXTURES / name)
        request.addfinalizer(lambda: os.chdir(old))
    return enter


@pytest.mark.parametrize("name", ["metawork", "sample"])
def test_cli_build_then_check_iris(in_repo, name, tmp_path):
    in_repo(name)
    out = tmp_path / "site"
    assert main(["build", "--out", str(out), "--no-release-snapshots"]) == 0
    assert main(["check-iris", "--site", str(out)]) == 0
    next(out.glob("*/vocab/*/index.html")).unlink()
    assert main(["check-iris", "--site", str(out)]) == 1


def test_cli_validate_exit_codes(in_repo):
    in_repo("metawork")
    assert main(["validate", "examples/valid-groups.ttl", "examples/valid-decisions.ttl"]) == 0
    assert main(["validate", "examples/invalid-groups.ttl"]) == 1


def test_cli_site_class_hook(in_repo, tmp_path):
    in_repo("sample")
    hooks = tmp_path / "hooks_mod"
    hooks.mkdir()
    (hooks / "sample_hooks.py").write_text(
        "from ontology_tooling import Site\n"
        "class Hooked(Site):\n"
        "    def ontology_sections(self):\n"
        "        return '<h2>From the hook</h2>'\n")
    import sys
    sys.path.insert(0, str(hooks))
    try:
        out = tmp_path / "site"
        assert main(["build", "--out", str(out), "--no-release-snapshots", "--site-class", "sample_hooks:Hooked"]) == 0
        assert "From the hook" in (out / "sample" / "index.html").read_text()
        with pytest.raises(SystemExit):
            main(["build", "--out", str(out), "--site-class", "sample_hooks"])
    finally:
        sys.path.remove(str(hooks))
