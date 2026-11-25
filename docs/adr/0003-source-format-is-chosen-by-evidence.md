# 3. Each ontology's source format is chosen by evidence and checked in CI

Date: 2026-11-25

## Status

Proposed 2026-11-25.

Provenance: GlassFrog project proj_da454776a6434f63b9b23847adece120 (Platform Engineering), "Ontology-as-code starter toolchain selected and recorded in an ADR".

Constrained by: metawork-ontology ADR-0002 and vertical-development-ontology ADR-0002 (SKOS first, `inference="none"`); metawork-ontology ADR-0005 decisions 1 and 5 (shared tooling in Python, `validate()` with `inference="none"`); ontology-hub ADR-0001 decision 1 (the hub owns `registry.json`).

Deviates from: the organization's technology radar, which puts Python on Hold. This record adds Python code to this package under the exception for RDF tooling that metawork-ontology ADR-0005 decision 5 requests (software-architecture-excellence#101). It also adds Java (ROBOT and ELK, in Docker) to CI.

Specification: [docs/spec/source-format-gate.md](../spec/source-format-gate.md).

## Context

Both existing ontologies are SKOS first, with minimal RDFS/OWL, no reasoner
(`inference="none"`), and SHACL shapes as fitness functions. Both records name a
trigger on a competency question that needs inference (metawork-ontology
ADR-0002: "introduce an inference layer in a new ADR"; vertical-development-ontology
ADR-0002: "add the OWL axiom and a new ADR"). Nothing detects when that trigger
fires.

Planned models differ in kind:

- **Vocabularies** (Meta Work, Vertical Development): named concepts, labels,
  broader and narrower terms, mappings.
- **Record schemas** (for example a product's domain model): records with typed
  fields that code reads and writes. LinkML generates OWL, SHACL, JSON Schema
  and TypeScript types from one YAML schema.
- **Rule-bearing models** (for example Holacracy: a role in a sub-circle is also
  in the parent circle). These need inference.

The formats cannot be converted into each other without loss: LinkML's OWL
import keeps only what its metamodel can express, and OWL 2 DL is more
expressive than SKOS or LinkML. So the format is a hard choice for each
ontology. Two failure modes exist: the choice follows the wording of a
proposal, or a repository drifts from its format without a decision.

| Option | Expressiveness | Toolchain cost | TypeScript consumer fit | Reversibility |
|---|---|---|---|---|
| SKOS + SHACL for all | Low; no inference | Lowest (today's state) | Turtle only | Easy to extend later |
| LinkML for all | Medium; records, not rules | Medium (new tool) | High (generated types) | Hard for vocabularies with SKOS-XL lineage |
| OWL for all | High | High (Java reasoner in CI) | Low (no TypeScript reasoner) | Hard; invites modeling for its own sake (metawork-ontology ADR-0002) |
| **One format per ontology, chosen by evidence** | Fits each model | Pay only where needed | Fits each consumer | One ADR per change |

Facts behind the cost column: ELK reasons over the OWL 2 EL profile only;
HermiT, which covers OWL 2 DL, has had little recent activity; no OWL reasoner
exists for TypeScript or Node.js. Sources: the internal tool survey of
2026-11-17 (sections 4b and 12), from the projects' repositories.

Radar: not searched for LinkML, ROBOT or ELK; no Radar Sources table is
configured for this repository.

## Decision

Each ontology has exactly one source format: `skos-shacl` (the default),
`linkml` or `owl-el`. The format is chosen from fact questions in the ontology's
first ADR and from its competency questions, not from the wording of the
proposal. A test that runs every competency question with and without the ELK
reasoner decides whether inference is needed. A fitness function in CI keeps
each repository inside its format. OWL means OWL 2 EL, reasoned at build time;
packages ship the inferred result. The ontology hub records each ontology's
format and the ADR that set it, by its own decision
([ontology-hub#23](https://github.com/Integral-Productivity/ontology-hub/issues/23)).

## Consequences

**Positive**

- The format follows from what the competency questions need.
- When a competency question first needs inference, CI says so. The ontology's
  own trigger still requires its own new ADR.
- The format of every ontology is visible in one place, with its record.

**Negative**

- The test with the reasoner needs ROBOT and ELK, so Java and Docker are in CI
  for every ontology, not only `owl-el` ones. This extends `validate()`, which
  today runs with `inference="none"` only (metawork-ontology ADR-0005).
- The test is only as good as the competency questions. A missing question can
  hide a need for OWL. Review of the questions stays a human task.
- `linkml` adds a tool to learn. It is not used until a record schema with a
  real consumer exists.

## Verification

Not yet tested. The first pilot tests both:

1. Both existing ontologies pass the test with no difference (they stay
   `skos-shacl`).
2. A small `owl-el` model with one transitive property shows a difference.

## Trigger to revisit

- About 20 ontologies or proposals have a recorded format. Then evaluate a
  model-based classifier, measured against those cases, as a first sort.
- A competency question needs more than OWL 2 EL (for example negation or
  cardinality). Then decide the profile and reasoner again.
