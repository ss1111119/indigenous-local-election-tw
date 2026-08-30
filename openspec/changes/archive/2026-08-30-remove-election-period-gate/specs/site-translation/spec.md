## MODIFIED Requirements

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
