## ADDED Requirements

### Requirement: An election type present in the data is either presented or excluded by name
The site builder derives the set of election types from the long tables, so a type added to the data layer reaches the site by default. That default is wrong for types the project has decided not to present yet, and it is also wrong to let such a type disappear without anyone stating that it did.

Every election type present in the long tables SHALL either be presented on the site or appear in a declared exclusion list carrying the reason it is excluded. A type that is neither presented nor declared SHALL abort the build naming that type.

Aborting SHALL be preferred over skipping. A type that vanishes from the site because a build step silently stepped over it is indistinguishable from a type that was never there, and this project has already published a wrong figure that survived a full day because the check that would have caught it was never invoked.

#### Scenario: A new election type appears in the long tables
- **WHEN** the long tables carry an election type that is neither presented nor declared as excluded
- **THEN** the build SHALL abort naming that type, rather than omitting it from the site

#### Scenario: A type is deliberately not presented
- **WHEN** the project decides a type belongs in the data layer but not yet on the site
- **THEN** the exclusion SHALL be declared with its reason, so that the decision is visible where the omission happens

#### Scenario: An excluded type later becomes presentable
- **WHEN** an excluded type is to be presented
- **THEN** removing its declaration SHALL be sufficient to make the build require it, so that the declaration is the only place the decision lives

### Requirement: A presented type's national figures come from the source's own aggregate row
The site shows national electorate and turnout per election type. Those figures are read from the aggregate row the source publishes for that type, not recomputed by the site builder from detail rows.

Where an election type carries no such aggregate row, the builder SHALL NOT synthesise one. Synthesising it would place a figure on the site that the source never published, and would do so as a side effect of a build step rather than as a decision.

#### Scenario: A type has no aggregate row
- **WHEN** an election type in the long tables has no aggregate row of its own
- **THEN** the builder SHALL treat it as not presentable and require a declared exclusion, rather than summing detail rows to produce one

#### Scenario: Aggregate rows are split across files
- **WHEN** a type's aggregate figures are published as more than one row because the source splits the electorate across mutually exclusive files
- **THEN** those rows SHALL be added together, because each is a genuine published aggregate and neither alone is the national figure
