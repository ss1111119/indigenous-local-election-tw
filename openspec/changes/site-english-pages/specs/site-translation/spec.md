## ADDED Requirements

### Requirement: A Translation Does Not Weaken A Qualifier
The qualifiers on this project's figures are the project's substance, not its packaging. A translated page SHALL carry qualifiers of the same strength as the original, and the qualifier text SHALL be produced from a single declared source rather than written separately per language.

Translating a qualifier more fluently is the failure mode this guards against. A shorter, smoother rendering that drops "not the whole population", the coverage rate, or the current-term disclaimer is a defect, not a stylistic choice.

Where a qualifier exists in one language and not another, the page SHALL abort rather than publish the unqualified version.

#### Scenario: A qualifier string is missing in one language
- **WHEN** a declared string has a value in one language and not another
- **THEN** the generator SHALL abort and name the key, rather than emitting a page with the qualifier absent

#### Scenario: A translated page omits the current-term statement
- **WHEN** a translated page presents historical figures during an election period without the statement that they do not represent the current term
- **THEN** the check SHALL fail and name that page, on the same terms as the original-language page

#### Scenario: Coverage ordering in the translated page
- **WHEN** a translated page presents a figure derived from a subset of the population
- **THEN** the coverage rate and the nature of the subset SHALL precede any percentage in that section, as required of the original

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

### Requirement: Coverage Checks Traverse Every Published Page
Checks that assert coverage over published pages SHALL enumerate pages recursively. A coverage check that silently stops at the top directory fails in exactly the situation it exists to catch.

#### Scenario: Pages are added in a subdirectory
- **WHEN** published pages are added under a subdirectory of the published tree
- **THEN** the coverage checks SHALL include them, and a check that enumerates only the top level SHALL be treated as defective

### Requirement: A Self-Translated Page States That It Is Self-Translated
Where a translation has not been reviewed by a speaker of the target language, the page SHALL say so and SHALL name which language version governs.

The project cannot verify that its own translation carries the same force as the original. Stating this is what distinguishes an unreviewed translation from a claim of equivalence.

#### Scenario: A translated page is published without native review
- **WHEN** a page is translated by the project itself and no reviewer of the target language has checked it
- **THEN** the page SHALL state that it is a project translation and name the authoritative language version
