# 2. Ontologies are versioned dependencies: the version IRI names a release, npm carries it

Date: 2026-11-25

## Status

Proposed 2026-11-25.

Provenance: GlassFrog project proj_da454776a6434f63b9b23847adece120 (Platform Engineering), "Ontology-as-code starter toolchain selected and recorded in an ADR".

Constrained by: ontology-hub ADR-0003 (names under `w3id.org/integral-productivity`); metawork-ontology ADR-0004 decision 3 (versioning; the ADR is superseded in part by ontology-hub ADR-0001, and decision 3 still holds); metawork-ontology ADR-0005 (shared tooling in Python, `inference="none"`); vertical-development-ontology ADR-0007 (immutable release tags).

Deviates from: the organization's technology radar, which puts Python on Hold. This record adds Python code to this package under the exception for RDF tooling that metawork-ontology ADR-0005 decision 5 requests (software-architecture-excellence#101).

Specification: [docs/spec/ontology-dependencies.md](../spec/ontology-dependencies.md).

## Context

The ontologies of this organization are meant to be dependencies of other
repositories: skills and plugins that validate records, SDKs that need types,
and other ontologies that import terms. Today a consumer has two ways to get an
ontology, and neither is a dependency in the usual sense:

- **Copy a file as a fixture** and assert that it matches (Meta Work's CQ-15 in
  the plugin).
- **Fetch the current IRI** under `https://w3id.org/integral-productivity/<ontology>`
  (ontology-hub ADR-0003). That address always means "current"
  (metawork-ontology ADR-0004 §3, which still holds), so the content can change
  under the consumer.

metawork-ontology ADR-0002 names the trigger for this record: "The plugin wants
to read the vocabulary at runtime rather than compare a fixture → publish the
ontology as a versioned artifact (npm or a static URL under
`ontology.integralproductivity.com`)." No record decides between the two.

An ontology has two identities, and a dependency must keep both:

1. **The semantic identity:** the IRI of the ontology and of one release. RDF
   tools (`owl:imports`, XML catalogs, reasoners) use it.
2. **The artifact identity:** the exact bytes a consumer installed. Package
   managers use it (a version, a lockfile, an integrity hash).

No ontology package manager exists that keeps both. Options compared (from an
internal tool survey of 2026-11-17; the table is its section 13, reduced):

| Option | Semantic identity | Artifact identity | Reversibility | Operational overhead | Consumer familiarity |
|---|---|---|---|---|---|
| Copy the file into the consumer | Lost | Manual | Easy | Low, drifts | High |
| `owl:imports` of the current IRI | Yes, but moves | None | Easy | Low | Medium |
| Fetch the frozen snapshot at a version IRI, plus a pinned catalog | Yes | Manual hash; no lockfile | Easy | Network or vendored copy per consumer | Low |
| ODK import modules | Yes | Per build | Medium | High (OBO build system) | Low |
| Git submodule | No | Commit hash | Medium | Medium | Low |
| **Version IRI for meaning, npm for transport** | **Yes** | **Lockfile and integrity hash** | Medium (published versions are permanent) | Medium (publish step, token) | High (default stack is TypeScript on Node.js) |

The static-URL option already half exists: this package builds the dated
snapshots. It lacks a lockfile, an integrity check and an upgrade path that
consumers' tools understand. npm adds those, and it carries the same release.

Radar: not searched for npm or LinkML; no Radar Sources table is configured
for this repository.

## Decision

Each release of an ontology is identified by a version IRI (`owl:versionIRI`,
the address of its dated snapshot under `w3id.org/integral-productivity`), and
npm transports that release as `@integral-productivity/<ontology>-ontology`,
with the package version, `owl:versionInfo` and the git tag required to agree.
Consumers resolve version IRIs offline through an XML catalog generated from
their lockfile, so RDF tools keep the semantic identity and npm keeps the
artifact identity. Two versions of one ontology in one build are an error.
Releases follow semantic versioning, with the breaking-change rule defined for
ontologies in the specification. Public upstream ontologies that this
organization does not own are not repackaged; they are imported by their own
version IRIs.

## Consequences

**Positive**

- A consumer pins an ontology like any other dependency. Renovate or Dependabot
  can propose upgrades, and the lockfile records the exact bytes.
- RDF tools still see standard version IRIs and catalogs. Nothing needs npm at
  query time.
- The dated snapshot, which already exists, becomes the version IRI. The hub
  needs no new path; `/<ontology>/v/<version>/` resolves through the w3id 303
  rule to the hub host.

**Negative**

- Each ontology repository needs an npm publish step and a token (or trusted
  publishing) in CI.
- An npm version cannot be reused after publication. A wrong release is fixed
  by the next version, as for tags (vertical-development-ontology ADR-0007).
- The semver rule is a convention until a check enforces it.
- This package does not yet accept a base IRI on another host than the serving
  origin ([#7](https://github.com/Integral-Productivity/ontology-tooling/issues/7)).
  The version IRI depends on that.

**Not decided here**

- **SHACL in TypeScript consumers.** The shapes use SHACL-SPARQL, which
  `rdf-validate-shacl` does not run (metawork-ontology ADR-0005 decision 5).
  Decide before the first TypeScript consumer validates data.
- **Visibility.** Packages are public once their ontology is published. A
  private ontology (vertical-development-ontology ADR-0006) publishes no
  package.

## Verification

Not yet tested. The first ontology that publishes a package tests both:

1. Two installed versions of one ontology define the same IRIs twice, and the
   catalog builder fails on it.
2. `owl:imports` of a version IRI does not resolve from `node_modules` without
   the generated catalog, and resolves with it.

## Trigger to revisit

- A package manager that resolves version IRIs and lockfiles together is
  released and supports `owl:imports` catalogs.
- A consumer cannot use npm (for example a Python-only service). Then add a
  second transport with the same version rule.
