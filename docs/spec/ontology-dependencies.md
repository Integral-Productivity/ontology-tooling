# Specification: ontologies as versioned npm dependencies

Implements [ADR-0002](../adr/0002-ontologies-as-versioned-npm-dependencies.md). This
file holds the detail that the ADR leaves out. It can change by pull request without
a new ADR, as long as the ADR's decision still holds.

## Version IRI

- Ontology IRI (unchanged): `https://w3id.org/integral-productivity/<ontology>`.
- Version IRI: `https://w3id.org/integral-productivity/<ontology>/v/<version>/`, the
  address of the dated snapshot that this package already builds.
- `owl:versionInfo` equals `<version>`.

## Package

- Name: `@integral-productivity/<ontology>-ontology`.
- Version: `<version>`, the same as the tag `v<version>`.
- Contents: the Turtle file, the SHACL shapes, a JSON-LD context where one exists,
  and `catalog-v001.xml` that maps the version IRI to the Turtle file in the package.
- The release build fails if the tag, `package.json`, `owl:versionInfo` and the
  version IRI disagree.

## Consumer catalog

- A function in this package reads the installed ontology packages and writes one
  XML catalog for the consumer. Python first; a Node equivalent when the first
  TypeScript consumer needs it.
- It fails when two versions of one ontology are installed.

## Semantic versioning for ontologies

| Bump | When |
|---|---|
| Major | A term is removed or its IRI changes; a class or property changes meaning; a SHACL shape rejects data that it accepted before. |
| Minor | A term, label, mapping or shape is added, and all data that was valid stays valid. |
| Patch | A wording fix in a definition or comment, with no change in structure. |

A changed label is not a patch where the ontology's own ADRs require an ADR for it
(vertical-development-ontology ADR-0002 §7: "A changed concept or label needs an
ADR. A wording fix in a definition does not.").

## Upstream ontologies

An ontology that this organization does not own (for example PROV-O or SKOS) is
imported by its own version IRI, with a catalog entry to a pinned copy.
