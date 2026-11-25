# Specification: source format gate

Implements [ADR-0003](../adr/0003-source-format-is-chosen-by-evidence.md). This file
holds the detail that the ADR leaves out. It can change by pull request without a
new ADR, as long as the ADR's decision still holds.

## Formats

| Value | For | Reasoner |
|---|---|---|
| `skos-shacl` | Vocabularies (default) | None |
| `linkml` | Record schemas | None |
| `owl-el` | Models whose competency questions need inference | ELK, at build time |

## Fact questions (in the ontology's first ADR)

1. Will code store and exchange records with typed fields? Yes: `linkml` is a candidate.
2. Is the main content a list of named concepts with labels and lineage? Yes: `skos-shacl` is a candidate.
3. Is there a competency question whose answer is not stated as a fact in the data? Yes: `owl-el` is a candidate.
4. Who is the first consumer, and does it read Turtle, generated types or JSON?

If question 3 is yes, it overrides the others.

## CQ-delta test

- Run every competency question on the asserted graph, then on the graph after ROBOT `reason` with ELK.
- `skos-shacl` or `linkml` with any difference: CI fails and lists the affected questions.
- `owl-el` with no difference: CI warns that the ontology pays for OWL without using it.

## Fitness functions (every pull request)

- `skos-shacl`: no OWL restrictions or class expressions beyond the minimal classes that instance data needs.
- `linkml`: the source is the LinkML YAML; generated OWL, SHACL and types are build outputs, not committed sources.
- `owl-el`: every axiom is inside OWL 2 EL (ROBOT `validate-profile --profile EL`).

## Hub registry

Decided in ontology-hub, tracked in [ontology-hub#23](https://github.com/Integral-Productivity/ontology-hub/issues/23).
