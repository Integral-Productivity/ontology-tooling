"""The site build: addressing, hub rules, renderers and hooks, against every fixture ontology."""
import html
import re
import shutil
from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, SKOS

import ontology_tooling as ot
from ontology_tooling.site import Site

SAMPLE = Path(__file__).parent / "fixtures" / "sample" / "ontology" / "sample.ttl"


def text(path):
    """Visible text of an HTML file, whitespace collapsed."""
    raw = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", path.read_text(encoding="utf-8"), flags=re.S)
    raw = re.sub(r"</?(a|b|code|span)\b[^>]*>", "", raw)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def test_package_writes_no_iri_by_hand():
    src = "".join(p.read_text(encoding="utf-8") for p in Path(ot.__file__).parent.glob("*.py"))
    # Repository names appear in docstrings that cite ADRs; hosts and IRIs never do.
    for host in ("integralproductivity.com", "example.org", "https://ontology."):
        assert host not in src


def test_every_minted_iri_maps_to_a_file(built, graph):
    out, site = built
    assert ot.missing_iris(graph, out) == []
    assert ot.hub_rule_violations(out, site.name) == []


def test_turtle_at_the_root_no_cname_nojekyll(built, ttl):
    out, site = built
    assert (out / f"{site.name}.ttl").read_bytes() == ttl.read_bytes()
    assert not (out / site.name / f"{site.name}.ttl").exists()
    assert not (out / "CNAME").exists()
    assert (out / ".nojekyll").is_file()


def test_hash_terms_are_anchors_on_the_ontology_page(built, graph):
    out, site = built
    raw = (out / site.name / "index.html").read_text(encoding="utf-8")
    for s in {str(x) for x in graph.subjects() if isinstance(x, URIRef)}:
        if s.startswith(site.base + "#"):
            assert f'id="{s[len(site.base) + 1:]}"' in raw, f"no anchor for {s}"


def test_definitions_are_the_ontologys_own_literals(built, graph):
    out, site = built
    for c in graph.subjects(RDF.type, SKOS.Concept):
        d = graph.value(c, SKOS.definition)
        if d is not None and site.path(c) and "#" not in site.path(c):
            assert " ".join(str(d).split()) in text(out / site.path(c).strip("/") / "index.html")


def test_current_version_snapshot(built, ttl):
    out, site = built
    snap = out / site.name / "v" / site.version
    assert (snap / f"{site.name}.ttl").read_bytes() == ttl.read_bytes()
    assert f"snapshot of version {site.version}" in text(snap / "index.html")


def test_root_page_points_at_the_prefix(built):
    out, site = built
    assert f'url={site.origin}/{site.name}/"' in (out / "index.html").read_text(encoding="utf-8")


def test_base_and_version_come_from_the_ontology_file(tmp_path):
    g = Graph().parse(SAMPLE, format="turtle")
    old, new = "https://example.org/sample", "https://onto.example.net/renamed"
    renamed = Graph()
    for s, p, o in g:
        s, o = (URIRef(str(x).replace(old, new)) if isinstance(x, URIRef) else x for x in (s, o))
        renamed.add((s, p, o))
    renamed.set((URIRef(new), OWL.versionInfo, Literal("9.9.9")))
    f = tmp_path / "renamed.ttl"
    renamed.serialize(f, format="turtle")
    out = tmp_path / "site"
    ot.build(out, f, releases={})
    assert (out / "renamed.ttl").exists()
    assert (out / "renamed" / "vocab" / "label" / "red-common" / "index.html").exists()
    assert (out / "renamed" / "v" / "9.9.9" / "index.html").exists()
    assert ot.missing_iris(renamed, out) == []


def test_skosxl_ordered_collection_and_sources_render_by_default(tmp_path):
    out = tmp_path / "site"
    ot.build(out, SAMPLE, releases={})
    red = text(out / "sample/vocab/red/index.html")
    assert "Labels Red, Scarlet" in red
    assert "Narrower Crimson" in red
    assert "Sources Newton, I. (1704)" in red
    assert "Members, in order Red, Green, Blue" in text(out / "sample/vocab/BandSequence/index.html")
    assert "Cited by Red" in text(out / "sample/source/spectrum-1704/index.html")
    assert "Literal form Scarlet" in text(out / "sample/vocab/label/scarlet-poetic/index.html")


# -- hooks -------------------------------------------------------------------

class BandSite(Site):
    def render(self, s):
        if URIRef(self.base + "#Band") in self.types(s):
            return self.page(self.name_of(s), f"<h1>Band: {self.name_of(s)}</h1>", self.crumbs("band"))
        return super().render(s)

    def resource_rows(self, s):
        return [*super().resource_rows(s), ("Hooked", "yes")]

    def ontology_sections(self):
        return "<h2>Custom section</h2>"

    def footer_extra(self):
        return ' · <a href="https://example.org/repo">source</a>'


def test_renderer_hooks_override_the_defaults(tmp_path):
    out = tmp_path / "site"
    ot.build(out, SAMPLE, BandSite, releases={})
    assert "Band: Red" in text(out / "sample/vocab/red/index.html")
    assert "Hooked yes" in text(out / "sample/vocab/Bands/index.html")
    onto = text(out / "sample/index.html")
    assert "Custom section" in onto and "source" in onto


def test_hub_rule_violations_name_each_broken_rule(built, tmp_path):
    out, site = built
    copy = tmp_path / "copy"
    shutil.copytree(out, copy)
    (copy / "CNAME").write_text("ontology.example.org")
    (copy / ".nojekyll").unlink()
    (copy / f"{site.name}.ttl").rename(copy / site.name / f"{site.name}.ttl")
    problems = " ".join(ot.hub_rule_violations(copy, site.name))
    for expected in ("CNAME", ".nojekyll", f"/{site.name}.ttl is missing", "belongs at"):
        assert expected in problems


def test_build_raises_on_a_broken_hub_rule(tmp_path, monkeypatch):
    import sys

    monkeypatch.setattr(sys.modules["ontology_tooling.build"], "hub_rule_violations", lambda out, name: ["site/CNAME exists"])
    with pytest.raises(ot.HubRuleError, match="CNAME"):
        ot.build(tmp_path / "site", SAMPLE, releases={})


def test_missing_page_is_reported(built, graph, tmp_path):
    out, site = built
    copy = tmp_path / "copy"
    shutil.copytree(out, copy)
    victim = site.page_subjects()[0]
    shutil.rmtree(copy / site.path(victim).strip("/"))
    assert str(victim) in ot.missing_iris(graph, copy)


def test_one_owl_ontology_required():
    g = Graph()
    with pytest.raises(ValueError, match="one owl:Ontology"):
        Site(g)
