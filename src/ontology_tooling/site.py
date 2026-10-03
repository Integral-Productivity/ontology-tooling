"""The Site: addressing, page frame, and the default renderers.

Started from vertical-development-ontology's tools/build_site.py ``Site`` class
(metawork-ontology ADR-0005, decision 1). The base IRI, prefix and version are
read from the one ``owl:Ontology`` in the file; no IRI is written here.

Renderer hooks (ADR-0005, decision 2). Subclass ``Site`` and override:

- ``render(iri)``          pick the page for a minted IRI (dispatch by type);
- ``resource_page(iri)``   the default page for a concept, scheme or other resource;
- ``resource_rows(iri)``   the rows of that page; extend instead of replacing it;
- ``ontology_sections()``  extra HTML sections on the ontology page;
- ``footer_extra()``       extra HTML in every page's footer;
- ``page_subjects()``      which IRIs get a page (default: every subject under ``<base>/``).

Domain helpers (lifting, label lookups) stay in each ontology repository.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from rdflib import Graph, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS

SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#5a5a5a;--line:#e3e3e3;--accent:#2a5d8f;--code:#f4f4f4;--warn:#8a5a00}
@media(prefers-color-scheme:dark){:root{--bg:#121212;--fg:#e8e8e8;--muted:#a0a0a0;--line:#2c2c2c;--accent:#7fb3e6;--code:#1e1e1e;--warn:#e0b050}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}a{color:var(--accent)}
h1{font-size:1.7rem;margin:.2em 0}h2{font-size:1.25rem;margin-top:2em;border-bottom:1px solid var(--line);padding-bottom:.25em}
h3{font-size:1.05rem;margin-top:1.6em}code{background:var(--code);padding:.1em .35em;border-radius:4px;font-size:.92em;overflow-wrap:anywhere}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.3em 1.2em}dt{color:var(--muted)}dd{margin:0}
.crumbs{color:var(--muted);font-size:.9em}.muted{color:var(--muted)}.warn{color:var(--warn)}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:.35em .5em;border-bottom:1px solid var(--line);vertical-align:top}
.term{scroll-margin-top:1em}footer{margin-top:3em;color:var(--muted);font-size:.85em;border-top:1px solid var(--line);padding-top:1em}
@media(max-width:600px){dl{grid-template-columns:1fr}dd{margin-bottom:.5em}table{display:block;overflow-x:auto}}
"""

e = html.escape


class Site:
    def __init__(self, g: Graph):
        self.g = g
        ontos = list(g.subjects(RDF.type, OWL.Ontology))
        if len(ontos) != 1:
            raise ValueError(f"expected one owl:Ontology, got {len(ontos)}: {ontos}")
        self.onto = ontos[0]
        self.base = str(self.onto).rstrip("/")
        url = urlparse(self.base)
        self.origin = f"{url.scheme}://{url.netloc}"
        self.name = url.path.strip("/")
        if not self.name or "/" in self.name:
            raise ValueError(f"the ontology IRI must be <origin>/<name>, got {self.base}")
        version = g.value(self.onto, OWL.versionInfo)
        if version is None:
            raise ValueError(f"{self.base} has no owl:versionInfo")
        self.version = str(version)
        self.ns = Namespace(self.base + "#")
        self.ttl_href = f"/{self.name}.ttl"

    # -- addressing -------------------------------------------------------

    def path(self, iri: URIRef) -> str | None:
        """Site path of an IRI minted under the base, or None for an external IRI."""
        s = str(iri)
        if s == self.base:
            return f"/{self.name}/"
        if s.startswith(self.base + "#"):
            return f"/{self.name}/#{s[len(self.base) + 1:]}"
        if s.startswith(self.base + "/"):
            return s[len(self.origin):].rstrip("/") + "/"
        return None

    def href(self, iri: URIRef) -> str:
        return self.path(iri) or str(iri)

    def page_subjects(self) -> list[URIRef]:
        """IRIs that get their own page: every subject minted under ``<base>/``."""
        return sorted({x for x in self.g.subjects() if isinstance(x, URIRef) and str(x).startswith(self.base + "/")})

    # -- reading ----------------------------------------------------------

    def lit(self, s, p) -> str:
        v = self.g.value(s, p)
        return " ".join(str(v).split()) if v is not None else ""

    def lits(self, s, p) -> list[str]:
        return sorted(" ".join(str(v).split()) for v in self.g.objects(s, p))

    def name_of(self, iri: URIRef) -> str:
        for p in (SKOS.prefLabel, SKOSXL.literalForm, RDFS.label, DCTERMS.title):
            if v := self.lit(iri, p):
                return v
        return str(iri).rstrip("/").split("/")[-1].split("#")[-1]

    def cite(self, src: URIRef) -> str:
        """Short form of a source's rdfs:label: author and year, else its first sentence."""
        label = self.lit(src, RDFS.label)
        m = re.match(r"^(.*?\(\d{4}[^)]*\))", label)
        return m.group(1) if m else label.split(". ")[0]

    def link(self, iri, text: str | None = None) -> str:
        if not isinstance(iri, URIRef):
            return e(text or str(iri))
        return f'<a href="{e(self.href(iri))}">{e(text or self.name_of(iri))}</a>'

    def links(self, iris) -> str:
        return ", ".join(self.link(x) for x in self.by_label(iris))

    def src_links(self, s) -> str:
        out = []
        for x in sorted(self.g.objects(s, DCTERMS.source)):
            out.append(self.link(x, self.cite(x) if (x, None, None) in self.g else None) if isinstance(x, URIRef) else e(str(x)))
        return ", ".join(out)

    def types(self, s) -> set[URIRef]:
        return set(self.g.objects(s, RDF.type))

    def by_label(self, iris) -> list[URIRef]:
        return sorted(iris, key=lambda x: (self.name_of(x).lower(), str(x)))

    # -- page frame -------------------------------------------------------

    def title(self) -> str:
        return self.lit(self.onto, DCTERMS.title) or self.name

    def footer_extra(self) -> str:
        """Hook: extra HTML appended to every page's footer (e.g. a source-repository link)."""
        return ""

    def page(self, title: str, body: str, crumbs: str) -> str:
        lic = self.g.value(self.onto, DCTERMS.license)
        lic_html = f' · license: <a href="{e(str(lic))}">{e(str(lic))}</a>' if lic else ""
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<link rel="alternate" type="text/turtle" href="{self.ttl_href}"><style>{CSS}</style></head>
<body><main><div class="crumbs">{crumbs}</div>{body}
<footer>{e(self.title())} {e(self.version)}{lic_html} ·
machine-readable: <a href="{self.ttl_href}">{e(self.ttl_href.lstrip("/"))}</a>{self.footer_extra()}</footer></main></body></html>"""

    def crumbs(self, *parts: str) -> str:
        return " › ".join([f'<a href="/{self.name}/">{e(self.title())}</a>', *parts])

    @staticmethod
    def dl(rows: list[tuple[str, str]]) -> str:
        return "<dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows if v) + "</dl>"

    def notes(self, s) -> list[tuple[str, str]]:
        return [
            ("Scope note", "<br>".join(e(x) for x in self.lits(s, SKOS.scopeNote))),
            ("Change note", "<br>".join(e(x) for x in self.lits(s, SKOS.changeNote))),
            ("Note", "<br>".join(e(x) for x in self.lits(s, SKOS.note))),
            ("Example", "<br>".join(e(x) for x in self.lits(s, SKOS.example))),
        ]

    # -- default renderers --------------------------------------------------

    def render(self, s: URIRef) -> str:
        """Hook: the page for a minted IRI. Override to dispatch on your own types."""
        return self.resource_page(s)

    def kind(self, s: URIRef) -> str:
        return ", ".join(sorted(self.name_of(t) if self.path(t) else str(t).split("#")[-1].split("/")[-1] for t in self.types(s)))

    def resource_rows(self, s: URIRef) -> list[tuple[str, str]]:
        """Rows of the default page: SKOS concepts, schemes, collections, labels, sources."""
        g = self.g
        members = ""
        if SKOS.ConceptScheme in self.types(s):
            members = "<br>".join(
                self.link(m) + (f' <span class="muted">— {e(d)}</span>' if (d := self.lit(m, SKOS.definition)) else "")
                for m in self.by_label(g.subjects(SKOS.inScheme, s)))
        head = g.value(s, SKOS.memberList)
        ordered = ", ".join(self.link(m) for m in Collection(g, head)) if head is not None else ""
        cited = self.by_label(set(g.subjects(DCTERMS.source, s)) | set(g.subjects(PROV.wasDerivedFrom, s)))
        return [
            ("IRI", f"<code>{e(str(s))}</code>"),
            ("Notation", " ".join(f"<code>{e(n)}</code>" for n in self.lits(s, SKOS.notation))),
            ("Literal form", e(self.lit(s, SKOSXL.literalForm))),
            ("Definition", e(self.lit(s, SKOS.definition))),
            ("Citation", e(self.lit(s, RDFS.label)) if PROV.Entity in self.types(s) else ""),
            ("Also called", ", ".join(e(a) for a in self.lits(s, SKOS.altLabel))),
            ("Labels", self.links(list(g.objects(s, SKOSXL.prefLabel)) + list(g.objects(s, SKOSXL.altLabel)))),
            ("Members, in order", ordered),
            ("Broader", self.links(g.objects(s, SKOS.broader))),
            ("Narrower", self.links(set(g.objects(s, SKOS.narrower)) | set(g.subjects(SKOS.broader, s)))),
            ("Related", self.links(g.objects(s, SKOS.related))),
            *self.notes(s),
            ("In scheme", self.links(g.objects(s, SKOS.inScheme))),
            ("Top concepts", self.links(set(g.objects(s, SKOS.hasTopConcept)) | set(g.subjects(SKOS.topConceptOf, s)))),
            ("Concepts in this scheme", members),
            ("Sources", self.src_links(s)),
            ("Cited by", "<br>".join(self.link(c) for c in cited)),
        ]

    def resource_page(self, s: URIRef) -> str:
        title = self.name_of(s)
        body = f'<h1>{e(title)}</h1><p class="muted">{e(self.kind(s))}</p>{self.dl(self.resource_rows(s))}'
        return self.page(f"{title} — {self.title()}", body, self.crumbs("vocab"))

    def schema_html(self) -> str:
        """The #-terms (classes and properties under ``<base>#``), each with an anchor."""
        g, ns = self.g, str(self.ns)
        out = ""
        for cls in sorted(x for x in g.subjects(RDF.type, OWL.Class) if str(x).startswith(ns)):
            local = str(cls)[len(ns):]
            out += (f'<h3 class="term" id="{e(local)}"><code>{e(str(cls))}</code> — {e(self.lit(cls, RDFS.label))}</h3>'
                    f"<p>{e(self.lit(cls, RDFS.comment))}</p>")
        props = sorted({p for t in (OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property, OWL.AnnotationProperty)
                        for p in g.subjects(RDF.type, t) if str(p).startswith(ns)})
        if props:
            out += "<table><tr><th>Property</th><th>Domain</th><th>Range</th></tr>"
            for p in props:
                local = str(p)[len(ns):]
                dom, rng = g.value(p, RDFS.domain), g.value(p, RDFS.range)
                comment = self.lit(p, RDFS.comment)
                out += (f'<tr id="{e(local)}" class="term"><td><code>{e(str(p))}</code><br>{e(self.lit(p, RDFS.label))}'
                        + (f'<br><span class="muted">{e(comment)}</span>' if comment else "")
                        + f"</td><td>{self.link(dom) if dom is not None else ''}</td>"
                        f"<td>{self.link(rng) if rng is not None else ''}</td></tr>")
            out += "</table>"
        # Any other #-subject (an individual, a datatype) still needs its anchor.
        anchored = {str(x) for x in g.subjects(RDF.type, OWL.Class)} | {str(p) for p in props}
        rest = sorted(str(x) for x in g.subjects() if isinstance(x, URIRef) and str(x).startswith(ns) and str(x) not in anchored)
        if rest:
            out += "<ul>" + "".join(f'<li class="term" id="{e(x[len(ns):])}"><code>{e(x)}</code></li>' for x in rest) + "</ul>"
        return out

    def schemes_html(self) -> str:
        out = ""
        for sc in self.by_label(x for x in self.g.subjects(RDF.type, SKOS.ConceptScheme) if self.path(x)):
            n = len(set(self.g.subjects(SKOS.inScheme, sc)))
            out += f'<li>{self.link(sc)} <span class="muted">({n}) — {e(self.lit(sc, SKOS.definition))}</span></li>'
        return f"<ul>{out}</ul>" if out else ""

    def ontology_sections(self) -> str:
        """Hook: extra HTML sections on the ontology page, after the schemes and before the schema."""
        return ""

    def ontology_page(self, snapshot: bool = False) -> str:
        title = self.title()
        ttl = f"/{self.name}/v/{self.version}/{self.name}.ttl" if snapshot else self.ttl_href
        snap = (f'<p class="warn">This is the snapshot of version {e(self.version)}. The current version is at '
                f'<a href="/{self.name}/">/{e(self.name)}/</a>.</p>') if snapshot else ""
        schemes = self.schemes_html()
        schema = self.schema_html()
        body = f"""<h1>{e(title)}</h1>{snap}<p class="muted">version {e(self.version)} · base <code>{e(self.base)}</code></p>
<p>{e(self.lit(self.onto, DCTERMS.description))}</p>
<p>Download: <a href="{e(ttl)}">{e(self.name)}.ttl</a> (Turtle).
Version {e(self.version)} snapshot: <a href="/{self.name}/v/{e(self.version)}/">/{e(self.name)}/v/{e(self.version)}/</a>.</p>
{f"<h2>Concept schemes</h2>{schemes}" if schemes else ""}{self.ontology_sections()}
{f"<h2>Schema</h2>{schema}" if schema else ""}"""
        crumbs = self.crumbs(f"v{e(self.version)}") if snapshot else e(title)
        return self.page(f"{title} {self.version}" if snapshot else title, body, crumbs)

    def root_page(self) -> str:
        """Only reachable at the project-site URL; on the domain, "/" belongs to ontology-hub."""
        url = f"{self.origin}/{self.name}/"
        title = self.title()
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(title)}</title>
<meta http-equiv="refresh" content="0; url={e(url)}"><link rel="canonical" href="{e(url)}"></head>
<body><p>The {e(title)} is published at <a href="{e(url)}">{e(url)}</a>.</p></body></html>"""
