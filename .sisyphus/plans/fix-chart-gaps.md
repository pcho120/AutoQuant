# Fix Non-Trading Day Gaps in Candlestick Charts

## TL;DR

> **Quick Summary**: Candlestick charts in both Portfolio and Paper Trading tabs show empty gaps on weekends/holidays, making indicators look broken. Fix by adding Plotly `rangebreaks` to exclude non-trading days and hours.
> 
> **Deliverables**:
> - `utils.py` — shared helper `compute_rangebreaks()` function
> - `chart.py` — Portfolio tab chart with gaps removed
> - `paper_trading.py` — Paper Trading tab chart with gaps removed
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (utils) → Task 2+3 (both chart files) → Task 4 (visual QA)

---

## Context

### Original Request
User reported that candlestick charts and indicator subplots look broken because non-working days (weekends, holidays) appear as empty gaps on the x-axis. Both Portfolio and Paper Trading tabs are affected.

### Interview Summary
**Key Discussions**:
- Issue affects `chart.py:render_chart_section()` and `paper_trading.py:render_enhanced_chart()`
- Both use `make_subplots(shared_xaxes=True)` — one `update_xaxes()` fixes all subplot rows
- Fix is well-known Plotly API: `fig.update_xaxes(rangebreaks=[...])`

**Research Findings**:
- GitHub examples (OpenBB, FinanceDataReader, etc.) all use same pattern
- For daily data: compute missing dates from actual data vs full date range (covers weekends + holidays)
- For intraday data: also add `dict(bounds=[16, 9.5], pattern="hour")` to hide non-trading hours
- `shared_xaxes=True` means single `update_xaxes()` call applies to all subplots

### Metis Review
**Identified Gaps** (addressed):
- Intraday timezone handling: yfinance returns tz-aware timestamps, use `.normalize()` for date comparison
- `data.dropna()` runs before rangebreaks computation: compute from post-dropna index (correct)
- Empty/short data guard: return `[]` if `len(data_index) < 2`
- Code duplication: extract shared helper to `utils.py`
- No test infrastructure: use pytest with synthetic data (no Streamlit/Supabase dependency)

---

## Work Objectives

### Core Objective
Remove non-trading day/hour gaps from all candlestick charts so the x-axis shows only trading periods with continuous data.

### Concrete Deliverables
- `utils.py`: New file with `compute_rangebreaks(data_index, interval)` function
- `chart.py`: Add `fig.update_xaxes(rangebreaks=...)` before `st.plotly_chart()`
- `paper_trading.py`: Add `fig.update_xaxes(rangebreaks=...)` before `st.plotly_chart()`

### Definition of Done
- [ ] `1d` interval charts show no gaps between Friday and Monday
- [ ] `15m`/`1h` interval charts show no gaps between 4:00 PM and 9:30 AM
- [ ] Holiday gaps removed (computed from actual data)
- [ ] All indicator subplots align with candlestick x-axis
- [ ] App starts without errors

### Must Have
- Weekends removed from daily charts
- Holidays removed from daily charts (auto-detected via data gaps)
- Non-trading hours removed from intraday charts (15m, 1h)
- Both Portfolio tab and Paper Trading tab charts fixed
- Shared helper function to avoid code duplication

### Must NOT Have (Guardrails)
- MUST NOT change subplot configuration (rows, heights, shared_xaxes)
- MUST NOT modify indicator calculations (RSI, MACD, KDJ, CCI)
- MUST NOT change chart styling (colors, fonts, margins, hover behavior)
- MUST NOT modify yfinance download parameters
- MUST NOT change layout/UI outside of chart rendering
- MUST NOT add logging, monitoring, or error handling beyond existing patterns
- MUST NOT touch `portfolio.py` or `app.py`
- MUST NOT add complex abstraction layers — keep it minimal

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: YES (tests-after for the utility function)
- **Framework**: pytest (via `env/bin/python -m pytest`)

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI/Backend**: Use Bash — Run commands, assert output
- **Frontend/UI**: Use Playwright — Visual verification of chart rendering

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation):
└── Task 1: Create utils.py with compute_rangebreaks() [quick]

Wave 2 (After Wave 1 — both chart fixes in PARALLEL):
├── Task 2: Add rangebreaks to chart.py [quick]
└── Task 3: Add rangebreaks to paper_trading.py [quick]

Wave 3 (After Wave 2 — verification + commit):
└── Task 4: Visual QA + commit [quick, playwright]

Critical Path: Task 1 → Task 2/3 → Task 4
Parallel Speedup: Wave 2 tasks run in parallel
Max Concurrent: 2 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 2, 3 | 1 |
| 2 | 1 | 4 | 2 |
| 3 | 1 | 4 | 2 |
| 4 | 2, 3 | — | 3 |

### Agent Dispatch Summary

- **Wave 1**: 1 task — T1 → `quick`
- **Wave 2**: 2 tasks — T2 → `quick`, T3 → `quick`
- **Wave 3**: 1 task — T4 → `quick` + `playwright`

---

## TODOs

> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

- [ ] 1. Create `utils.py` with `compute_rangebreaks()` helper function

  **What to do**:
  - Create `utils.py` in project root with function `compute_rangebreaks(data_index, interval)`:
    - If `len(data_index) < 2`, return `[]`
    - Normalize dates: use `data_index.normalize()` to strip timezone/time for date comparison
    - Compute full date range: `pd.date_range(start=data_index.min().normalize(), end=data_index.max().normalize(), freq='D')`
    - Find missing dates: dates in full range but NOT in actual data dates
    - Build rangebreaks list with `dict(values=[list of missing date strings])`
    - For intraday intervals (`"15m"`, `"1h"`): also append `dict(bounds=[16, 9.5], pattern="hour")`
    - Return the rangebreaks list
  - Create `tests/test_rangebreaks.py` with pytest tests:
    - `test_daily_removes_weekends`: Mon-Fri DatetimeIndex → weekend dates in rangebreaks
    - `test_daily_removes_holidays`: DatetimeIndex missing a Wednesday → that date in rangebreaks
    - `test_intraday_includes_hour_bounds`: 15m/1h → result includes hour bounds dict
    - `test_intraday_also_removes_date_gaps`: intraday still computes missing dates
    - `test_empty_data_returns_empty`: empty index → returns `[]`
    - `test_single_point_returns_empty`: 1-element index → returns `[]`
    - `test_1d_no_hour_bounds`: daily interval → no hour bounds in result
  - Run `env/bin/python -m pytest tests/test_rangebreaks.py -v` → all pass

  **Must NOT do**:
  - Import Streamlit, Supabase, or yfinance in utils.py or tests
  - Add any chart rendering logic to utils.py
  - Create complex class hierarchies

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (foundation task)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2, Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `chart.py:18` — Available intervals: `["15m", "1h", "1d"]`
  - `chart.py:24` — `yf.download()` returns DatetimeIndex on `data.index`

  **External References**:
  - Plotly rangebreaks API: `fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"]), dict(values=[dates])])`
  - GitHub pattern (FinanceDataReader): compute `dt_breaks` by comparing `pd.date_range` against actual index dates

  **WHY Each Reference Matters**:
  - `chart.py:18`: Shows the exact interval values the function must handle ("15m", "1h", "1d")
  - `chart.py:24`: Shows the data source — yfinance returns only trading days, so gaps = non-trading days

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All unit tests pass
    Tool: Bash
    Preconditions: utils.py and tests/test_rangebreaks.py created
    Steps:
      1. Run: env/bin/python -m pytest tests/test_rangebreaks.py -v
      2. Assert: exit code 0, all 7 tests PASSED
    Expected Result: 7 passed, 0 failed
    Failure Indicators: Any FAILED test, ImportError, SyntaxError
    Evidence: .sisyphus/evidence/task-1-tests-pass.txt

  Scenario: Import works standalone
    Tool: Bash
    Preconditions: utils.py exists
    Steps:
      1. Run: env/bin/python -c "from utils import compute_rangebreaks; print('OK')"
      2. Assert: stdout is "OK"
    Expected Result: Clean import, no errors
    Failure Indicators: ImportError, ModuleNotFoundError
    Evidence: .sisyphus/evidence/task-1-import-ok.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-tests-pass.txt — pytest output
  - [ ] task-1-import-ok.txt — import verification

  **Commit**: NO (groups with final commit)

- [ ] 2. Add rangebreaks to `chart.py` (Portfolio tab)

  **What to do**:
  - Add `from utils import compute_rangebreaks` at top of `chart.py` (after line 6, with other imports)
  - Add these lines before `st.plotly_chart(fig, ...)` (before line 143):
    ```python
    rangebreaks = compute_rangebreaks(data.index, interval)
    if rangebreaks:
        fig.update_xaxes(rangebreaks=rangebreaks)
    ```
  - Verify no other changes to the file

  **Must NOT do**:
  - Modify subplot configuration, indicator calculations, or styling
  - Change any existing line of code
  - Add error handling beyond what exists

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `chart.py:143` — `st.plotly_chart(fig, use_container_width=True)` — Insert rangebreaks BEFORE this line
  - `chart.py:1-6` — Import block — add new import here
  - `chart.py:18` — `interval` variable is defined here, accessible at insertion point

  **WHY Each Reference Matters**:
  - `chart.py:143`: Exact insertion point — rangebreaks must be set before rendering
  - `chart.py:1-6`: Where to add the import to follow existing conventions
  - `chart.py:18`: Confirms `interval` is available as a local variable in the function scope

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Minimal diff — only import + 3 lines added
    Tool: Bash
    Preconditions: Edit completed
    Steps:
      1. Run: git diff chart.py
      2. Assert: exactly 1 import line added, 3 logic lines added, 0 lines removed/modified
    Expected Result: 4 lines added total, nothing else changed
    Failure Indicators: More than 4 lines changed, any deletions
    Evidence: .sisyphus/evidence/task-2-diff.txt

  Scenario: Syntax valid
    Tool: Bash
    Preconditions: Edit completed
    Steps:
      1. Run: env/bin/python -c "import chart; print('OK')"
      2. Assert: stdout contains "OK" (may have Streamlit warnings, that's fine)
    Expected Result: No SyntaxError
    Failure Indicators: SyntaxError, IndentationError
    Evidence: .sisyphus/evidence/task-2-syntax.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-diff.txt — git diff output
  - [ ] task-2-syntax.txt — syntax verification

  **Commit**: NO (groups with final commit)

- [ ] 3. Add rangebreaks to `paper_trading.py` (Paper Trading tab)

  **What to do**:
  - Add `from utils import compute_rangebreaks` at top of `paper_trading.py` (after line 9, with other imports)
  - Add these lines before `st.plotly_chart(fig, ...)` in `render_enhanced_chart()` (before line 520):
    ```python
    rangebreaks = compute_rangebreaks(data.index, interval)
    if rangebreaks:
        fig.update_xaxes(rangebreaks=rangebreaks)
    ```
  - Verify no other changes to the file

  **Must NOT do**:
  - Modify subplot configuration, indicator calculations, or styling
  - Touch any function other than `render_enhanced_chart()`
  - Change any existing line of code

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 2)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `paper_trading.py:520` — `st.plotly_chart(fig, use_container_width=True)` — Insert rangebreaks BEFORE this line
  - `paper_trading.py:1-9` — Import block — add new import here
  - `paper_trading.py:391` — `interval` variable is defined here, accessible at insertion point

  **WHY Each Reference Matters**:
  - `paper_trading.py:520`: Exact insertion point in `render_enhanced_chart()`
  - `paper_trading.py:1-9`: Import convention to follow
  - `paper_trading.py:391`: Confirms `interval` is a local variable accessible at the insertion point

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Minimal diff — only import + 3 lines added
    Tool: Bash
    Preconditions: Edit completed
    Steps:
      1. Run: git diff paper_trading.py
      2. Assert: exactly 1 import line added, 3 logic lines added, 0 lines removed/modified
    Expected Result: 4 lines added total, nothing else changed
    Failure Indicators: More than 4 lines changed, any deletions
    Evidence: .sisyphus/evidence/task-3-diff.txt

  Scenario: Syntax valid
    Tool: Bash
    Preconditions: Edit completed
    Steps:
      1. Run: env/bin/python -c "import py_compile; py_compile.compile('paper_trading.py', doraise=True); print('OK')"
      2. Assert: stdout contains "OK"
    Expected Result: No SyntaxError
    Failure Indicators: SyntaxError, IndentationError
    Evidence: .sisyphus/evidence/task-3-syntax.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-diff.txt — git diff output
  - [ ] task-3-syntax.txt — syntax verification

  **Commit**: NO (groups with final commit)

- [ ] 4. Visual QA verification + commit

  **What to do**:
  - Start Streamlit app: `env/bin/streamlit run app.py --server.headless true --server.port 8599`
  - Use Playwright to verify charts in Portfolio tab:
    - Select a stock, set interval to `1d`, period `1mo`
    - Screenshot — verify no weekend/holiday gaps
    - Set interval to `1h`, period `5d`
    - Screenshot — verify no overnight gaps
  - Verify app starts without errors
  - Kill Streamlit process
  - Run unit tests: `env/bin/python -m pytest tests/test_rangebreaks.py -v`
  - Stage and commit: `utils.py`, `chart.py`, `paper_trading.py`, `tests/test_rangebreaks.py`
  - Commit message: `fix: remove non-trading day/hour gaps from candlestick charts`

  **Must NOT do**:
  - Stage files other than `utils.py`, `chart.py`, `paper_trading.py`, `tests/test_rangebreaks.py`
  - Push to remote
  - Modify any code (this task is verification + commit only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`playwright`, `git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: None
  - **Blocked By**: Task 2, Task 3

  **References**:

  **Pattern References**:
  - `app.py:13-23` — Tab navigation: `tab1` (Portfolio) has chart at bottom
  - `chart.py:14` — Stock selector: `st.selectbox("Choose a stock", ...)`
  - `chart.py:16-18` — Period/interval selectors

  **WHY Each Reference Matters**:
  - `app.py:13-23`: Explains the app structure — Portfolio tab renders chart via `chartManager`
  - `chart.py:14-18`: Identifies the UI controls Playwright needs to interact with

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Portfolio chart — daily interval has no gaps
    Tool: Playwright
    Preconditions: App running on port 8599, Tasks 2-3 completed
    Steps:
      1. Navigate to http://localhost:8599
      2. Portfolio tab should be active by default
      3. Select interval "1d" and period "1mo" in chart controls
      4. Take screenshot of the candlestick chart area
      5. Verify: no visible empty gaps between Friday and Monday candles
    Expected Result: Continuous candlestick chart with no weekend gaps
    Failure Indicators: Visible empty spaces between trading days
    Evidence: .sisyphus/evidence/task-4-portfolio-daily.png

  Scenario: Portfolio chart — intraday has no overnight gaps
    Tool: Playwright
    Preconditions: App running, daily chart verified
    Steps:
      1. Change interval to "1h" and period "5d"
      2. Take screenshot of the candlestick chart area
      3. Verify: no visible gaps between 4:00 PM and 9:30 AM
    Expected Result: Continuous intraday chart
    Failure Indicators: Large empty spaces between trading sessions
    Evidence: .sisyphus/evidence/task-4-portfolio-intraday.png

  Scenario: Unit tests still pass
    Tool: Bash
    Preconditions: All code changes complete
    Steps:
      1. Run: env/bin/python -m pytest tests/test_rangebreaks.py -v
      2. Assert: all tests pass
    Expected Result: 7 passed, 0 failed
    Failure Indicators: Any FAILED test
    Evidence: .sisyphus/evidence/task-4-tests-pass.txt

  Scenario: Clean commit
    Tool: Bash
    Preconditions: All verification passed
    Steps:
      1. Run: git add utils.py chart.py paper_trading.py tests/test_rangebreaks.py
      2. Run: git commit -m "fix: remove non-trading day/hour gaps from candlestick charts"
      3. Assert: exit code 0
      4. Run: git diff HEAD~1 --name-only
      5. Assert: exactly 4 files listed
    Expected Result: Clean commit with 4 files
    Failure Indicators: Unexpected files, commit failure
    Evidence: .sisyphus/evidence/task-4-commit.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-portfolio-daily.png — screenshot of daily chart
  - [ ] task-4-portfolio-intraday.png — screenshot of intraday chart
  - [ ] task-4-tests-pass.txt — pytest output
  - [ ] task-4-commit.txt — git log output

  **Commit**: YES
  - Message: `fix: remove non-trading day/hour gaps from candlestick charts`
  - Files: `utils.py`, `chart.py`, `paper_trading.py`, `tests/test_rangebreaks.py`

---

## Final Verification Wave

> Not needed for this small fix. Task 4 covers visual QA + commit.

---

## Commit Strategy

- **Single commit** after all tasks verified:
  - Message: `fix: remove non-trading day/hour gaps from candlestick charts`
  - Files: `utils.py`, `chart.py`, `paper_trading.py`

---

## Success Criteria

### Verification Commands
```bash
env/bin/python -c "from utils import compute_rangebreaks; print('OK')"  # Expected: OK
env/bin/python -m pytest tests/test_rangebreaks.py -v  # Expected: all tests pass
timeout 15 env/bin/streamlit run app.py --server.headless true --server.port 8599 2>&1 | head -5  # Expected: "You can now view"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] Charts show no weekend/holiday gaps
- [ ] Intraday charts show no overnight gaps
- [ ] All indicator subplots aligned with candlestick
