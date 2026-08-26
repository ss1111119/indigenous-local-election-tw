# site-editorial-neutrality Specification

## Purpose

確保站台的導覽標籤與頁面標題不使用比底層資料實際能支持的更強的解讀性字眼（例如把候選人得票率暗示為政黨認同），讓讀者從導覽與標題就能準確判斷頁面內容的範圍與限制。

## Requirements

### Requirement: Navigation labels and page headings do not overclaim beyond what the data supports
The `<nav>` and `<h1>` elements of every published page under `docs/` SHALL NOT contain wording that implies a stronger interpretive claim than the underlying data supports (specifically the terms "政黨傾向", "政黨版圖", "party leaning", and "Party Politics"), while such terms remain permitted in body content where they are used to draw a boundary rather than to characterize the page as a whole.

#### Scenario: A navigation label using an overclaiming term fails the check
- **WHEN** any page's `<nav>` element contains the string "政黨傾向", "政黨版圖", "party leaning", or "Party Politics"
- **THEN** the build aborts with an error naming the file, the element (`nav`), and the term found

#### Scenario: A heading using an overclaiming term fails the check
- **WHEN** any page's `<h1>` element contains one of the same four terms
- **THEN** the build aborts with an error naming the file, the element (`h1`), and the term found

#### Scenario: The same term used correctly in body content does not trigger a false positive
- **WHEN** a page's body content outside `<nav>` and `<h1>` (for example a qualifying sentence that says a given figure is not this term, or a translated string used the same way) contains "政黨傾向" or "party leaning"
- **THEN** the check does not raise an error

#### Scenario: The five published pages pass the check
- **WHEN** `scripts/build_site_data.py` is run with `--check` or `--write` against the current `docs/index.html`, `docs/roster.html`, `docs/legislative.html`, `docs/en/index.html`, and `docs/en/legislative.html`
- **THEN** the check passes for all five files

<!-- @trace
source: neutral-legislative-page-naming
updated: 2026-08-26
code:
  - README.md
  - docs/legislative.html
  - docs/index.html
  - docs/roster.html
  - docs/en/legislative.html
  - docs/en/index.html
  - scripts/build_site_data.py
tests:
  - scripts/test_build_site_data.py
-->