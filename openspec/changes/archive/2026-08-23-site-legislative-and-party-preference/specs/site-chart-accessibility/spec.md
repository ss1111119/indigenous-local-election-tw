## MODIFIED Requirements

### Requirement: Color Verification Is Recorded, Not Asserted
Any claim that a palette is readable SHALL be recorded with the tool used, the color-vision-deficiency types simulated, the threshold applied, and the measured values. A bare statement that a palette was "checked" SHALL NOT satisfy this requirement.

A record SHALL be reproducible by a later reader: it SHALL name the command that produced it, and the command SHALL be one that can fail. Where a palette grows a new series, the record SHALL cover every pair of the enlarged palette rather than only the pairs the previous record covered.

#### Scenario: A palette or ink is changed
- **WHEN** a series fill or a label ink is added or re-stepped
- **THEN** the record SHALL name the tool, the simulated deficiency types, the threshold, and the resulting numbers for every pair or combination affected, so a later reader can tell a measurement from an opinion

##### Example: the record this change carries

| Field | Value |
| --- | --- |
| tool | `scripts/palette_metrics.py` in this repo (OKLab ΔE ×100; Machado 2009 CVD matrices on linear RGB) for separation; WCAG relative-luminance contrast for inks. Calibrated against an external validator to ≤0.04 for normal vision and ≤0.03 for protan/deutan |
| CVD types simulated | protan, deutan (in-repo tool). tritan measured once with the external validator (9.6 light / 15.1 dark) and **not reproducible in-repo** — see `palette_metrics.py` docstring |
| thresholds | ΔE 15 normal vision / ΔE 8 CVD for adjacent pairs; 4.5:1 for text inside a mark |
| measured | separation 16.9 (light) / 16.6 (dark), CVD 9.0 / 9.7; eight ink-on-fill combinations 4.58–8.41 |

##### Example: the six-series legislative palette

| Field | Value |
| --- | --- |
| why a second palette | the legislative page needs five party buckets, not three: 親民黨 took 27.7% in 2001 and 無黨團結聯盟 26.0% in 2004, and the local-office three-bucket set drops both into 其他 |
| pairs measured | all 15 pairs, not the 5 adjacent ones — a legend that wraps on a narrow screen puts non-adjacent series next to each other |
| light fills | `#2a78d6 #1baf7a #ee7700 #c0397a #3A4046 #ADB3B9`; worst normal ΔE 16.9, worst CVD ΔE 9.0 |
| dark fills | `#3987e5 #1da77a #ee7700 #cc2244 #C9CED3 #6A7178`; worst normal ΔE 16.6, worst CVD ΔE 9.3 |
| inks inside marks | light 4.76–10.49, dark 4.89–11.23 (floor 4.5:1) |
| record | `docs/schema/palette-legislative.md`, holding the unedited output of both commands |
| the measurement can fail | 親民黨 `#ee7700`→`#22b884` gives 2 failing pairs, exit 1; 無黨團結聯盟's ink `#fff`→`#16181A` gives 3.48:1, exit 1; unmutated baseline exits 0 |

#### Scenario: Only a claim is offered
- **WHEN** a change states that colors were verified but names no tool, no simulation, and no numbers
- **THEN** the claim SHALL be treated as unverified, because "checked" is not reproducible

##### Example: what does and does not count as a record

| Statement | Counts |
| --- | --- |
| "配色已檢查，色盲下可辨識" | no — no tool, no type, no number |
| "palette_metrics.py，protan/deutan，門檻 ΔE 8，實測 9.0／9.7" | yes |

#### Scenario: The recorded numbers are all passes
- **WHEN** a record shows every measured pair above the threshold
- **THEN** the record SHALL also show that the measurement is capable of reporting a failure, by naming a mutation of the palette that the same command rejects, because a check that cannot fail records nothing
