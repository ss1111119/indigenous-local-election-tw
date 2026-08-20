# site-data-generation Specification

## ADDED Requirements

### Requirement: Constant-To-Long-Table Consistency Is Enforced, Not Merely Checkable
The comparison between the embedded site constants and the long tables SHALL be executed by the test suite, not left to a command someone remembers to run. A difference that is not in the named-and-explained list SHALL fail the suite.

#### Scenario: The bucketing logic changes but the site is not regenerated
- **WHEN** a change to party identity mapping, seat attribution, or any other derivation alters a value the site already publishes
- **THEN** the test suite SHALL fail naming the differing keys, so the site cannot stay on stale figures while the dataset moves on

##### Example: the drift this would have caught on the day it appeared

| Key | Site constant | Long tables | Consequence if unnoticed |
| --- | ---: | ---: | --- |
| `T2.2005.party.無黨籍[0]` | 0 | 7 | seven seats attributed to 「其他各政黨」 |
| `T3.2005.party.無黨籍[0]` | 0 | 8 | eight seats attributed to 「其他各政黨」 |
| `T3.1998.party.其他[0]` | 4 | 1 | inflated aggregate bucket |


#### Scenario: A difference is intended
- **WHEN** the generator legitimately adds keys the site does not yet carry, such as a newly introduced field
- **THEN** those keys SHALL be listed as expected additions and SHALL NOT fail the suite, while any unlisted difference still does

##### Example: intended additions versus drift

| Difference | Listed as expected | Suite result |
| --- | --- | --- |
| new `mainSequence` field on every type | yes | passes |
| new `types` array | yes | passes |
| a seat count that changed value | no | fails, naming the key |

