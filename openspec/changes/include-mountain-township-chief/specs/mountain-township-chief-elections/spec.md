## ADDED Requirements

### Requirement: A mountain indigenous township is identified by administrative code, never by name
The mountain township chief is an office reserved by statute, but the source files do not label it. Selecting it requires matching the official designation list against the election files, and that match SHALL be performed on the (province, county, township) code triple rather than on place names.

Name matching SHALL NOT be used at build time, because it both under-selects and mis-selects: the designation list writes 霧台鄉 where the election files write 霧臺鄉, writes five units under their post-2010 district names while the term in question still had them as townships, and names 那瑪夏 which appeared as 三民鄉 before 2008 — while more than ten unrelated 三民 villages exist nationwide.

#### Scenario: A township is selected for a term
- **WHEN** the build selects the rows belonging to a mountain indigenous township
- **THEN** it SHALL match on the code triple recorded for that term, and SHALL NOT compare place names

#### Scenario: A name variant appears in the source
- **WHEN** a township appears in the source under a different name than the designation list uses
- **THEN** it SHALL still be selected, because the code triple is what identifies it

#### Scenario: A name is shared by unrelated units
- **WHEN** a place name in the designation list also occurs as the name of units that are not mountain indigenous townships
- **THEN** the selection SHALL NOT include those units

### Requirement: The code mapping is recorded per term, not as a single snapshot
Administrative codes are renumbered across terms, and the set of qualifying townships changes for reasons that differ between terms. The mapping from code triple to township SHALL therefore carry the term as part of its key.

The record SHALL be data that can be inspected row by row, not a rule that derives one term's codes from another's. Deriving them SHALL NOT be relied upon, because the two reductions in the set have different causes — units whose parent county was being reorganised and did not hold that election, versus units that were reorganised into indigenous districts and moved to a different election type.

#### Scenario: Codes differ between two terms for the same township
- **WHEN** the same township carries different administrative codes in two terms
- **THEN** both SHALL appear in the record, each under its own term

#### Scenario: A term is missing from the record
- **WHEN** the build processes a term for which the record holds no rows
- **THEN** it SHALL abort and name that term, rather than selecting nothing

### Requirement: Selection is verified by a per-term count that fails when selection silently returns nothing
The defect this guards against does not raise an error. Stripping the source of its value-prefix quoting, or matching on the wrong field, yields zero selected units and a build that completes successfully with an empty result.

The build SHALL assert the number of townships selected for each term against a recorded expected count, and SHALL abort naming the term and the actual count when they differ.

#### Scenario: Selection returns nothing
- **WHEN** a term's selection matches no units
- **THEN** the build SHALL abort and name that term, and SHALL NOT emit a term with no rows

#### Scenario: Selection returns fewer units than expected
- **WHEN** a term's selection matches a number of units that differs from the recorded expected count
- **THEN** the build SHALL abort and name both the expected and the actual count

### Requirement: The mountain township chief series is not joined to the indigenous district chief series
Six mountain indigenous townships were reorganised into indigenous districts, and their chief elections moved to a different election type from that term onward. The two series therefore describe the same units under two office classifications, and joining them produces an apparent change in seat count that did not occur.

The two election types SHALL NOT be placed in a single sequence, and the constraint SHALL be enforced by a check rather than recorded only in documentation.

#### Scenario: The two types are placed in one sequence
- **WHEN** the mountain township chief type and the indigenous district chief type would be treated as one continuous series
- **THEN** the check SHALL fail and name both types

#### Scenario: The count falls between two terms
- **WHEN** the number of mountain township chief units decreases between two terms
- **THEN** the reason SHALL be recorded per term, because a reorganisation and a non-participating county are different causes and neither is a change in representation

### Requirement: The mountain township chief type is a subset of an official type, and is marked as project-defined
The official election type covers all township chiefs, of which the mountain indigenous townships are a part. Naming the subset with the official code would make the type name disagree with the official code table this project treats as authoritative for type names.

The subset SHALL carry a project-defined type code registered alongside this project's other project-defined codes, and SHALL be classified as an indigenous election type.

#### Scenario: The type name is read from the long table
- **WHEN** a consumer reads the election type name for these rows
- **THEN** it SHALL be a project-defined name, distinguishable from the official code table's entry for all township chiefs

#### Scenario: Indigenous election types are enumerated
- **WHEN** the set of indigenous election types is enumerated
- **THEN** the mountain township chief type SHALL be included
