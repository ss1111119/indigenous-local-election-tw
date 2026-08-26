# mountain-township-chief-census Specification

## Purpose

The chief of a mountain indigenous township is an office reserved by statute for
mountain indigenous persons (Local Government Act art. 57 §2), and the
indigenous districts the project already covers were reorganised out of those
townships in 2014. Deciding whether the earlier elections can be covered
requires an authoritative list of which townships qualify in which term, and a
per-term record of what the source files actually look like. This capability
governs that census: where the list comes from and for how long each entry
applies, how availability is recorded per term, and the boundary that the
census reports what the data looks like without deciding inclusion or deriving
any figure from it.

## Requirements

### Requirement: The mountain indigenous township list is sourced from an official designation and scoped by effective period
Separating mountain indigenous townships from the source election files requires a list of which administrative units qualify, because the source files carry only county and township codes and never state the category. That list SHALL come from an official government designation with its provenance recorded, and SHALL NOT be compiled by the project from names, secondary summaries, or inference.

Because administrative reorganisation moves units between categories over time, the list SHALL record an effective period per unit rather than a single current snapshot, and a unit that leaves the category SHALL be retained with its end date rather than deleted.

#### Scenario: A unit is reorganised out of the category
- **WHEN** a mountain indigenous township is reorganised into a different administrative category, as five were when the special municipality indigenous districts were created
- **THEN** its row SHALL remain in the list with an end date, so that terms before the reorganisation still resolve

#### Scenario: No official designation can be found
- **WHEN** no official government designation of the list can be located and verified
- **THEN** the census SHALL record that no official source was found, and SHALL NOT substitute a secondary compilation or a list assembled by the project

#### Scenario: A term is matched against the list
- **WHEN** records from a given term are matched against the list
- **THEN** the census SHALL state which version of the list applied to that term and on what date basis it was selected


<!-- @trace
source: census-mountain-township-chief
updated: 2026-08-26
code:
  - docs/schema/山地鄉鄉長資料清點.md
  - README.md
  - data/sources.json
  - data/reference/mountain-township-list.csv
-->

---
### Requirement: Source availability is censused per term, and absence of a defect is distinguished from absence of checking
The census SHALL open and record each source folder containing township chief data individually. A finding from one term SHALL NOT be generalised to another term, because this project has already established that county codes are renumbered per file across the earlier terms and that one legislative term uses an entirely different code system.

For each known class of source defect, the census SHALL record one of three states per term — confirmed present with counts and samples, confirmed absent with the method used to confirm it, or not checked. Recording a defect class as absent when it was merely not observed SHALL be treated as a defect in the census itself.

#### Scenario: A defect class is not mentioned for a term
- **WHEN** the census does not state a finding for a known defect class in a given term
- **THEN** that SHALL be recorded explicitly as not checked, rather than left silent to be read as absent

#### Scenario: Two terms are censused
- **WHEN** one term's files are found to match the list cleanly
- **THEN** no conclusion SHALL be drawn about any other term's files without opening them


<!-- @trace
source: census-mountain-township-chief
updated: 2026-08-26
code:
  - docs/schema/山地鄉鄉長資料清點.md
  - README.md
  - data/sources.json
  - data/reference/mountain-township-list.csv
-->

---
### Requirement: The census does not decide inclusion and produces no derived figures
The census establishes what the source data looks like. Deciding whether the office joins the published datasets is a separate judgement that carries its own constraints, including the publication rules that apply during an election period.

The census SHALL NOT modify the published long tables, SHALL NOT add an election type code, SHALL NOT alter any published page, and SHALL NOT compute any ratio, share, or other figure derived by dividing across populations.

#### Scenario: The census finds the data is clean and matchable
- **WHEN** the census concludes that a term's data can be matched to the list without defects
- **THEN** it SHALL record that finding and stop, without adding the records to any published dataset

#### Scenario: A summary figure would be convenient
- **WHEN** stating how many mountain indigenous township chief seats exist would make the report easier to read
- **THEN** a raw count of units or records is permitted, but any figure formed by dividing one population by another SHALL NOT be produced

<!-- @trace
source: census-mountain-township-chief
updated: 2026-08-26
code:
  - docs/schema/山地鄉鄉長資料清點.md
  - README.md
  - data/sources.json
  - data/reference/mountain-township-list.csv
-->