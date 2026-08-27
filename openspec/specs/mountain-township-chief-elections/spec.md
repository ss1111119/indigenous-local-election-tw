# mountain-township-chief-elections Specification

## Purpose

The chief of a mountain indigenous township is reserved by statute for mountain
indigenous persons, and the indigenous districts this project already covers
were reorganised out of those townships. Covering the office is not a matter of
reading one more source folder: the official election type covers every township
chief in the country, so the qualifying units are a subset that has to be
selected — and the source names them inconsistently enough that selecting by name
both under-matches and mis-matches.

This capability governs that selection and its boundaries. Selection is by
administrative code, recorded per term because the codes are renumbered and the
qualifying set changes for reasons that differ between terms. Selection is
verified by comparing sets rather than counts, because the failures that matter
keep the count intact. Ingestion stops at the level where the figures are sound,
because one of the defects below that level produces a complete run and a wrong
answer. And the resulting series is kept separate from the indigenous district
chief series, because the two describe the same units under two office
classifications and joining them invents a change that did not occur.

## Requirements

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

---
### Requirement: The code mapping is recorded per term, not as a single snapshot
Administrative codes are renumbered across terms, and the set of qualifying townships changes for reasons that differ between terms. The mapping from code triple to township SHALL therefore carry the term as part of its key.

The record SHALL be data that can be inspected row by row, not a rule that derives one term's codes from another's. Deriving them SHALL NOT be relied upon, because the two reductions in the set have different causes — units whose parent county was being reorganised and did not hold that election, versus units that were reorganised into indigenous districts and moved to a different election type.

#### Scenario: Codes differ between two terms for the same township
- **WHEN** the same township carries different administrative codes in two terms
- **THEN** both SHALL appear in the record, each under its own term

#### Scenario: A term is missing from the record
- **WHEN** the build processes a term for which the record holds no rows
- **THEN** it SHALL abort and name that term, rather than selecting nothing

---
### Requirement: Selection is verified by a per-term count that fails when selection silently returns nothing
The defect this guards against does not raise an error. Stripping the source of its value-prefix quoting, or matching on the wrong field, yields zero selected units and a build that completes successfully with an empty result.

The build SHALL assert the number of townships selected for each term against a recorded expected count, and SHALL abort naming the term and the actual count when they differ.

#### Scenario: Selection returns nothing
- **WHEN** a term's selection matches no units
- **THEN** the build SHALL abort and name that term, and SHALL NOT emit a term with no rows

#### Scenario: Selection returns fewer units than expected
- **WHEN** a term's selection matches a number of units that differs from the recorded expected count
- **THEN** the build SHALL abort and name both the expected and the actual count

---
### Requirement: The mountain township chief series is not joined to the indigenous district chief series
Six mountain indigenous townships were reorganised into indigenous districts, and their chief elections moved to a different election type from that term onward. The two series therefore describe the same units under two office classifications, and joining them produces an apparent change in seat count that did not occur.

The two election types SHALL NOT be placed in a single sequence, and the constraint SHALL be enforced by a check rather than recorded only in documentation.

#### Scenario: The two types are placed in one sequence
- **WHEN** the mountain township chief type and the indigenous district chief type would be treated as one continuous series
- **THEN** the check SHALL fail and name both types

#### Scenario: The count falls between two terms
- **WHEN** the number of mountain township chief units decreases between two terms
- **THEN** the reason SHALL be recorded per term, because a reorganisation and a non-participating county are different causes and neither is a change in representation

---
### Requirement: The mountain township chief type is a subset of an official type, and is marked as project-defined
The official election type covers all township chiefs, of which the mountain indigenous townships are a part. Naming the subset with the official code would make the type name disagree with the official code table this project treats as authoritative for type names.

The subset SHALL carry a project-defined type code registered alongside this project's other project-defined codes, and SHALL be classified as an indigenous election type.

#### Scenario: The type name is read from the long table
- **WHEN** a consumer reads the election type name for these rows
- **THEN** it SHALL be a project-defined name, distinguishable from the official code table's entry for all township chiefs

#### Scenario: Indigenous election types are enumerated
- **WHEN** the set of indigenous election types is enumerated
- **THEN** the mountain township chief type SHALL be included

---
### Requirement: Ingestion stops at the level the figures are sound at
The source files carry rows below the township level whose figures are not sound in every term. A census of all seven terms found three defects that exist only below township level: a profile file whose candidate and elected counts are a constant that contradicts its own ratio column, a profile row whose valid and invalid votes do not sum to its own turnout, and a votes file in which every detail row carries the elected mark.

The mountain township chief type SHALL be ingested only at township level and above. The restriction SHALL be enforced by the build rather than left to whoever runs it, and the enforcement SHALL name the level and the term when it rejects a row.

The third defect SHALL be treated as the reason the restriction is enforced rather than merely documented: the first two abort the build when they are met, but a file in which every candidate is marked elected produces a complete run and a wrong answer.

#### Scenario: A row below township level is encountered
- **WHEN** the build reads a mountain township chief row at village or polling-station level
- **THEN** it SHALL exclude that row from the long tables, and the exclusion SHALL follow from a stated level rule rather than from the row happening to fail another check

#### Scenario: Deeper levels are proposed later
- **WHEN** ingestion below township level is proposed for any term
- **THEN** each of the three named defects SHALL first be resolved for that term, and the absence of a build error SHALL NOT be accepted as evidence that they are absent

#### Scenario: The restriction would drop data that is needed
- **WHEN** the level restriction is applied
- **THEN** it SHALL be confirmed that the figures this capability covers survive it, because each qualifying township is itself a township-level unit

---
### Requirement: A district column that disagrees across source files is normalised, not trusted and not ignored
In five of the seven terms the district column holds different values in different files for the same unit, and in the profile file it varies by level within a single file. A cross-file join on that column matches nothing, and the failure is silent.

Where the column disagrees, it SHALL be normalised before any cross-file comparison, and the values each file is permitted to carry SHALL be recorded per file so that a third value appearing later aborts rather than passing through normalisation unnoticed. Normalising the column SHALL NOT relax any other reconciliation.

#### Scenario: The column disagrees between two files of one term
- **WHEN** two source files of the same term carry different district values for the same unit
- **THEN** the column SHALL be normalised for that term and the permitted values SHALL be recorded per file

#### Scenario: A value outside the recorded set appears
- **WHEN** a source file carries a district value that the record does not list for it
- **THEN** the build SHALL abort naming the term and the file, rather than normalising it away

#### Scenario: A term's files already agree
- **WHEN** every source file of a term carries the same district value
- **THEN** no normalisation SHALL be registered for that term, because an unnecessary entry would hide a later divergence
