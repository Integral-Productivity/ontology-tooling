# ontology-tooling

Shared code for the Integral Productivity ontologies: the static site that makes every
minted IRI resolve, the checks the ontology hub depends on, and SHACL validation. Each
ontology repository keeps its own domain code and, where its model needs it, renderer
hooks.

Decided in [metawork-ontology ADR-0005](https://github.com/Integral-Productivity/metawork-ontology/blob/main/docs/adr/0005-shared-tooling-package-and-reusable-workflow.md):
a Python package plus reusable workflows, no template repository. The repository
layout itself (README, ADRs, competency questions, shapes, licence) comes from the
`ontology-scaffold` skill, not from here.

## What it owns

| Part | Where |
|---|---|
| Page frame and CSS | `ontology_tooling.Site.page`, `CSS` |
| IRI → site path (`<base>` → `/<name>/`, `<base>#X` → `/<name>/#X`, `<base>/p` → `/<name>/p/`) | `Site.path` |
| Hub rules: Turtle at `/<name>.ttl`, no `site/CNAME`, `.nojekyll` ([ontology-hub ADR-0002](https://github.com/Integral-Productivity/ontology-hub/blob/main/docs/adr/0002-turtle-at-root-and-unlisted-entries.md)). The build fails if one breaks. | `hub_rule_violations`, `HubRuleError` |
| Dated snapshots `/<name>/v/<version>/` for the current version and every `vX.Y.Z` tag; a released file may not change without a version bump ([metawork-ontology ADR-0004](https://github.com/Integral-Productivity/metawork-ontology/blob/main/docs/adr/0004-one-domain-many-ontologies.md) decision 3, behavior from vertical-development-ontology#6) | `released`, `snapshots`, `ReleaseError` |
| Every minted IRI maps to a file | `missing_iris`, `check_site`, `ontology-tooling check-iris` |
| `load()` / `validate()`: ontology merged into the data graph, `inference="none"`, SHACL-SPARQL on | `ontology_tooling.shacl` |
| Default renderers for SKOS concepts, schemes, ordered collections, SKOS-XL labels, cited sources, and the ontology page | `Site.resource_page`, `Site.ontology_page` |

The base IRI, the prefix and the version are read from the one `owl:Ontology` in the
Turtle file (its IRI must be `<origin>/<name>`, with an `owl:versionInfo`). Nothing in
the package names a host.

## Use it from an ontology repository

`requirements.txt`:

```
ontology-tooling @ git+https://github.com/Integral-Productivity/ontology-tooling@v0.1.1
```

`.github/workflows/pages.yml`:

```yaml
name: pages
on:
  push: { branches: [main] }
  pull_request:
  workflow_dispatch:
jobs:
  pages:
    uses: Integral-Productivity/ontology-tooling/.github/workflows/pages.yml@v0.1.1
    permissions: { contents: read, pages: write, id-token: write }
    # with:
    #   site-class: site_hooks:MySite          # renderer hooks, in tools/site_hooks.py
    #   extra-check: python -m pytest -q tests/test_site.py
```

`.github/workflows/validate.yml`:

```yaml
name: validate
on:
  push: { branches: [main] }
  pull_request:
jobs:
  validate:
    uses: Integral-Productivity/ontology-tooling/.github/workflows/validate.yml@v0.1.1
    with:
      examples: |
        examples/valid-groups.ttl
        examples/valid-groups.ttl examples/valid-decisions.ttl
```

Pin the same tag in `requirements.txt` and in both `uses:` lines, and bump them together.

### Workflow inputs

`pages.yml`: `python-version` (3.12), `working-directory` (.), `install`
(`-r requirements.txt`), `ontology` (the one `ontology/*.ttl`), `site-class`,
`release-snapshots` (true), `extra-check`, `deploy` (true). The build and IRI check
run on pull requests and on `main`. The deploy runs only from `main`, never on a pull
request, and never while the calling repository is private.

`validate.yml`: `python-version`, `working-directory`, `install`, `ontology`, `shapes`
(`shapes`), `examples` (one line per data graph that must conform; files on a line are
merged), `test-command` (`python -m pytest -q`).

### Command line

Run from the ontology repository's root:

```bash
ontology-tooling build --out site [--site-class site_hooks:MySite] [--no-release-snapshots]
ontology-tooling check-iris --site site
ontology-tooling validate examples/a.ttl examples/b.ttl
```

Exit status 0 is success, 1 is a failed check, 2 is a usage error.

## Renderer hooks

Subclass `Site` and override only what the model needs. The hook interface is a public
API between repositories: changing it is a breaking release.

| Hook | Default |
|---|---|
| `render(iri)` | `resource_page(iri)` for every minted IRI; dispatch on your own types here |
| `resource_rows(iri)` | IRI, notation, definition, labels, broader/narrower/related, notes, scheme members, sources, cited-by |
| `resource_page(iri)` | title, kind, `resource_rows` |
| `ontology_sections()` | nothing; HTML added after the concept schemes |
| `footer_extra()` | nothing; HTML added to every footer |
| `page_subjects()` | every subject IRI under `<base>/` |

```python
# tools/site_hooks.py
from ontology_tooling import Site

class MySite(Site):
    def footer_extra(self):
        return ' · <a href="https://github.com/Integral-Productivity/my-ontology">source</a>'
```

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e '.[test]' && .venv/bin/pytest -q
```

The tests build, check and validate read-only copies of real ontologies under
`tests/fixtures/`: metawork-ontology, and a synthetic `sample` with
vertical-development-ontology's shape (SKOS-XL labels, an ordered collection, sources as
IRIs). VDO itself is private until its publication gate opens, so it is not copied
here ([#2](https://github.com/Integral-Productivity/ontology-tooling/issues/2)). CI also
runs both reusable workflows against the fixtures, with deploy off.

Python is on Hold in the org technology radar except for ML tooling; ADR-0005 decision 5
asks for an exception for RDF tooling
([software-architecture-excellence#101](https://github.com/Integral-Productivity/software-architecture-excellence/issues/101)).

## Licence

MIT. See [LICENSE](LICENSE).
