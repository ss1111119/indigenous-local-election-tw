## ADDED Requirements

### Requirement: An Identity Lookup Is Keyed So That Re-Numbered Codes Cannot Collide
The generator resolves administrative codes to display names by building lookup tables from the long tables. In the legacy terms the source re-numbers county codes per file, so the same raw code denotes different counties in different election types. A lookup keyed on the raw code therefore holds two meanings for one key. This is the administrative-code form of a failure this capability already governs for party identity, where a single-field key silently merged distinct sources.

Where the generator builds a lookup from an administrative code to a name, the key SHALL be one under which a single entry cannot denote two different places. For county identity the key SHALL use the normalized county code produced by the project's county code crosswalk, not the raw source code, so that the generator and the data layer resolve identity through the same table. Every column such a key depends on SHALL be declared among the columns the generator requires, so that its disappearance from a long table aborts the build rather than silently restoring the defective behavior.

Where two records supply different names for one key, the generator SHALL abort and SHALL name the key and both names. It SHALL NOT keep whichever record it read last. A lookup that resolves a key to the wrong name produces a label that is confidently wrong and looks entirely ordinary, so the collision SHALL be surfaced at build time rather than left to be noticed on a published page.

Changing the key SHALL NOT reduce the lookup's coverage. Where a candidate key would resolve fewer records than the key it replaces, that loss SHALL be treated as a defect of the replacement rather than an acceptable cost of removing the collision, because an unresolved name and a wrong name are both failures of the same lookup.

#### Scenario: One raw code denotes two counties across election types
- **WHEN** the same raw county code appears in two election types of one term and the source assigns it to a different county in each
- **THEN** each record SHALL resolve to its own county, because the key distinguishes them through the crosswalk rather than through the order in which the records were read

#### Scenario: Two names arrive for one key
- **WHEN** two records supply different names for the same lookup key
- **THEN** the generator SHALL abort naming the key and both names, rather than retaining the last one written

#### Scenario: The column the key depends on is absent
- **WHEN** a long table lacks the normalized code column the lookup keys on
- **THEN** the generator SHALL abort, because falling back to the raw code would silently reinstate the collision

#### Scenario: A proposed key resolves fewer records
- **WHEN** a candidate key removes the collision but leaves records unresolved that the previous key resolved
- **THEN** that key SHALL be rejected, because trading a visible wrong label for an absent one does not fix the lookup

#### Scenario: Normalization is valid only at the level it was built for
- **WHEN** a normalized code is used as a lookup key below the level at which the crosswalk establishes it
- **THEN** that SHALL be treated as out of the crosswalk's scope rather than an extension of it
