# site-translation Specification

## Purpose

A translation is not a copy in another language. It is a second set of claims,
made by whoever wrote it, about what the first set said. This project's substance
is its qualifiers — a coverage rate, a statement that a figure is not about the
whole population, a note that a number does not represent the current election —
and qualifiers are exactly what translation erodes. The erosion is not malicious
and does not look like an error: a shorter, more fluent rendering that drops
"not the whole population" reads better than the original.

This capability exists because that erosion is invisible to every other check in
this project. The data can be identical, the charts can be identical, the page
can pass every accessibility and generation rule, and the translated page can
still promise more than the original does.

The rules therefore attach to mechanism rather than to intent. Qualifier text is
generated from one declared source, so the two languages cannot drift apart.
Static qualifier text stays in the page's own markup — a qualifier that depends
on script execution is a qualifier that can vanish — and a check asserts it
matches the declared source word for word. Every display label carries its
provenance, so a name this project invented is never presented as an official
one. Where no established name exists, the original is kept rather than a new one
coined. And a translation nobody qualified has reviewed says so, and names which
language governs.

One rule here is not about language at all: coverage checks must enumerate pages
recursively. It lives here because a second language is what first created a
subdirectory, and a coverage check that stops at the top level fails silently in
exactly the situation it was written to catch.

## Requirements

### Requirement: A Translation Does Not Weaken A Qualifier
The qualifiers on this project's figures are the project's substance, not its packaging. A translated page SHALL carry qualifiers of the same strength as the original, and the qualifier text SHALL be produced from a single declared source rather than written separately per language.

Translating a qualifier more fluently is the failure mode this guards against. A shorter, smoother rendering that drops "not the whole population", the coverage rate, or the current-term disclaimer is a defect, not a stylistic choice.

Where a qualifier exists in one language and not another, the page SHALL abort rather than publish the unqualified version.

The current-term statement is required because the published figures end at a term earlier than the one the reader may assume, which is true of the data regardless of whether an election is under way. Its enforcement SHALL NOT be conditioned on any election phase.

#### Scenario: A qualifier string is missing in one language
- **WHEN** a declared string has a value in one language and not another
- **THEN** the generator SHALL abort and name the key, rather than emitting a page with the qualifier absent

#### Scenario: A translated page omits the current-term statement
- **WHEN** a translated page presents historical figures without the statement that they do not represent the current term
- **THEN** the check SHALL fail and name that page, on the same terms as the original-language page

#### Scenario: The statement is treated as conditional on an election being under way
- **WHEN** the current-term statement is removed on the grounds that no election is currently in progress
- **THEN** the check SHALL still fail and name that page, because the statement describes the span of the data rather than the electoral calendar

#### Scenario: Coverage ordering in the translated page
- **WHEN** a translated page presents a figure derived from a subset of the population
- **THEN** the coverage rate and the nature of the subset SHALL precede any percentage in that section, as required of the original


<!-- @trace
source: site-english-pages
updated: 2026-08-24
code:
  - AGENTS.md
  - scripts/build_site_data.py
  - docs/en/index.html
  - docs/en/legislative.html
  - docs/sitemap.xml
  - .spectra.yaml
  - docs/index.html
  - scripts/mutate_build_site_data.py
  - CLAUDE.md
  - GEMINI.md
  - HANDOFF.md
  - docs/roster.html
  - README.md
  - docs/legislative.html
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Display Labels Are Declared With Their Provenance
A translated label is a claim about what something is called. The project SHALL declare each display label's translation together with where that translation comes from, and SHALL distinguish an official name from one the project coined.

Provenance SHALL be one of: published by the responsible authority, the organisation's own published English name, or coined by this project. A label coined by this project SHALL be presented to readers in a way that does not imply official standing.

Where no established English name exists, retaining the original-language name SHALL be preferred over coining one, unless the label is required to understand the page's main finding.

#### Scenario: A label has no established English name
- **WHEN** an entity appearing only in supporting detail has no official or widely used English name
- **THEN** the original-language name SHALL be retained and the page SHALL say so, rather than a coined name being presented as if established

#### Scenario: A coined label is required for comprehension
- **WHEN** a label must be translated for the page's main finding to be readable
- **THEN** it SHALL be translated, marked as coined by this project, and shown with the original-language name at first occurrence so a reader can look it up

#### Scenario: A declared label lacks provenance
- **WHEN** a label translation is declared without a provenance value, or with a value outside the permitted set
- **THEN** the generator SHALL abort and name that label


<!-- @trace
source: site-english-pages
updated: 2026-08-24
code:
  - AGENTS.md
  - scripts/build_site_data.py
  - docs/en/index.html
  - docs/en/legislative.html
  - docs/sitemap.xml
  - .spectra.yaml
  - docs/index.html
  - scripts/mutate_build_site_data.py
  - CLAUDE.md
  - GEMINI.md
  - HANDOFF.md
  - docs/roster.html
  - README.md
  - docs/legislative.html
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Coverage Checks Traverse Every Published Page
Checks that assert coverage over published pages SHALL enumerate pages recursively. A coverage check that silently stops at the top directory fails in exactly the situation it exists to catch.

#### Scenario: Pages are added in a subdirectory
- **WHEN** published pages are added under a subdirectory of the published tree
- **THEN** the coverage checks SHALL include them, and a check that enumerates only the top level SHALL be treated as defective


<!-- @trace
source: site-english-pages
updated: 2026-08-24
code:
  - AGENTS.md
  - scripts/build_site_data.py
  - docs/en/index.html
  - docs/en/legislative.html
  - docs/sitemap.xml
  - .spectra.yaml
  - docs/index.html
  - scripts/mutate_build_site_data.py
  - CLAUDE.md
  - GEMINI.md
  - HANDOFF.md
  - docs/roster.html
  - README.md
  - docs/legislative.html
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: A Self-Translated Page States That It Is Self-Translated
Where a translation has not been reviewed by a speaker of the target language, the page SHALL say so and SHALL name which language version governs.

The project cannot verify that its own translation carries the same force as the original. Stating this is what distinguishes an unreviewed translation from a claim of equivalence.

#### Scenario: A translated page is published without native review
- **WHEN** a page is translated by the project itself and no reviewer of the target language has checked it
- **THEN** the page SHALL state that it is a project translation and name the authoritative language version

<!-- @trace
source: site-english-pages
updated: 2026-08-24
code:
  - AGENTS.md
  - scripts/build_site_data.py
  - docs/en/index.html
  - docs/en/legislative.html
  - docs/sitemap.xml
  - .spectra.yaml
  - docs/index.html
  - scripts/mutate_build_site_data.py
  - CLAUDE.md
  - GEMINI.md
  - HANDOFF.md
  - docs/roster.html
  - README.md
  - docs/legislative.html
tests:
  - scripts/test_build_site_data.py
-->