## ADDED Requirements

### Requirement: Shared verification helpers carry mutation-test proof of discriminating power
Any function in `scripts/oracles.py` that a mutation-test script's test-selection filter can reach SHALL have that filter actually include the tests exercising it, and the corresponding mutation-test script SHALL contain at least one real-file mutation per shared function proven, by manual apply-and-revert verification, to turn the exercising test from passing to failing.

#### Scenario: A mutation-test script's selection filter is not silently stale
- **WHEN** a new test function is added to a `test_build_*.py` file that exercises a function in `scripts/oracles.py`
- **THEN** the corresponding `mutate_build_*.py` script's test-selection filter is updated to include that test function's name, so the mutation suite does not silently skip evaluating it

#### Scenario: check_population_column has a real-file mutation
- **WHEN** `check_population_column`'s finite-value check is removed via a real-file mutation applied to `scripts/oracles.py`
- **THEN** running the exercising test through the mutation-test script's harness reports the test as failing, and reverting the mutation restores it to passing

#### Scenario: write_oracle_document has a real-file mutation
- **WHEN** `write_oracle_document`'s write step is bypassed via a real-file mutation applied to `scripts/oracles.py`
- **THEN** running the exercising test through the mutation-test script's harness reports the test as failing, and reverting the mutation restores it to passing

#### Scenario: _render_manifest_sections has a real-file mutation covering the party-list call site
- **WHEN** the call to `_render_manifest_sections` that renders `PARTY_LIST_MANIFEST` is removed via a real-file mutation applied to `scripts/oracles.py`
- **THEN** running the exercising test through the mutation-test script's harness reports the test as failing, and reverting the mutation restores it to passing
