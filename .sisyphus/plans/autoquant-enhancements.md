# AutoQuant Enhancements: Ticker Filtering & Editable Holdings

## TL;DR

> **Quick Summary**: Add ticker search filtering to Paper Trading and AI Prediction tabs, plus editable holdings table to Paper Trading tab with granular DB updates.
> 
> **Deliverables**:
> - Reusable ticker search component (streamlit-searchbox)
> - Paper Trading tab: Editable holdings table synced to DB
> - AI Prediction tab: Ticker search replaces text input
> - Granular DB update methods (update_position, delete_position)
> 
> **Estimated Effort**: Medium (8-10 tasks, ~6-8 hours work)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 3 → Task 7 → Task 10

---

## Context

### Original Request (Korean)
1. Paper trading으로 보유한 주식을 portfolio에 있는 테이블처럼 보여줘
2. 모든 탭에 ticker 입력할 때 회사 이름 또는 티커 입력하면 연관검색어처럼 보여줘 (A 타입하면 A로 시작하는 티커들)
3. Portfolio supabase 데이터베이스 상호작용 개선

### Interview Summary
**Key Discussions**:
- Q1 (streamlit-searchbox): ✅ YES - 승인됨
- Q2 (Paper Trading 편집): ✅ 편집 가능, DB 수정
- Q3 (Portfolio 상호작용): ✅ 현재 상태 OK (DB 읽기/쓰기 작동 중)
- Q4 (Ticker 필터링 방식): ✅ "A 타입 → A*" 접두사 필터링 (자동완성 아님)
- Q5 (성능): ✅ 기본값 (150ms, 1시간 캐시)

**Research Findings** (5 parallel background agents):
- **DB Schema**: holdings 테이블 (독립적), orders 테이블 (insert-only)
- **Current Pattern**: Full-replace (DELETE all + INSERT), granular UPDATE/DELETE 없음
- **st.data_editor**: Portfolio 탭에 이미 존재, on_change=None, edited_rows 미사용
- **Ticker Filtering**: streamlit-searchbox가 접두사 필터링 지원, legacy 코드에 예제 있음

---

## Work Objectives

### Core Objective
Enable ticker search filtering and editable Paper Trading holdings with DB persistence.

### Concrete Deliverables
- `components/ticker_search.py` — Reusable search component
- `adapters/db_client.py` — update_position(), delete_position() methods
- `ui/paper_trading_tab.py` — Ticker search + editable holdings table
- `ui/prediction_tab.py` — Ticker search input
- Updated `requirements.txt` — streamlit-searchbox dependency

### Definition of Done
- [ ] streamlit-searchbox installed and cached ticker list works
- [ ] Paper Trading tab displays holdings from DB in editable table
- [ ] Edits to Paper Trading holdings persist to DB via granular updates
- [ ] Ticker search filters by prefix ("A" → "AAPL", "AMZN") in 2 tabs
- [ ] All existing tests pass (no regressions)

### Must Have
- Editable Paper Trading holdings table (st.data_editor)
- Granular DB updates (row-level UPDATE/DELETE)
- Ticker prefix filtering in Paper Trading and AI Prediction tabs
- Current market price display for Paper Trading holdings

### Must NOT Have (Guardrails)
- Do NOT modify Portfolio tab (current implementation already works)
- Do NOT add ticker filtering to Portfolio data_editor column (technical complexity)
- Do NOT change orders table structure (keep insert-only)
- Do NOT aggregate positions from orders (use independent holdings table)
- Do NOT implement full autocomplete (only prefix filtering: "A" → "A*")

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest, 16 tests, 100% pass)
- **Automated tests**: Tests-after (add tests for new methods)
- **Framework**: pytest + pytest-mock

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **UI Testing**: Use `bash` (manual Streamlit app verification, screenshots)
- **Backend/API**: Use `bash` (pytest, import tests)
- **Database**: Use `bash` (SQL queries via Supabase CLI or python)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — 3 tasks, parallel):
├── Task 1: Install streamlit-searchbox + update requirements.txt [quick]
├── Task 2: Create ticker_search.py component [quick]
└── Task 3: Add granular DB methods (update_position, delete_position) [quick]

Wave 2 (UI Replacements — 2 tasks, parallel, after Task 2):
├── Task 4: Replace ticker input in Paper Trading tab [quick]
└── Task 5: Replace ticker input in AI Prediction tab [quick]

Wave 3 (Paper Trading Holdings — 5 tasks, sequential, after Task 3):
├── Task 6: Add fetch_positions + prices to Paper Trading [quick]
├── Task 7: Render editable holdings table [unspecified-high]
├── Task 8: Implement Save handler with granular updates [deep]
├── Task 9: Add error handling and user feedback [quick]
└── Task 10: Write tests for new DB methods and UI flow [unspecified-high]

Critical Path: T1 → T3 → T6 → T7 → T8 → T10
Parallel Speedup: ~40% faster than sequential
Max Concurrent: 3 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|------------|--------|------|
| 1 | — | 2, 4, 5 | 1 |
| 2 | 1 | 4, 5 | 1 |
| 3 | — | 6, 7, 8 | 1 |
| 4 | 2 | — | 2 |
| 5 | 2 | — | 2 |
| 6 | 3 | 7 | 3 |
| 7 | 6 | 8 | 3 |
| 8 | 7 | 9, 10 | 3 |
| 9 | 8 | 10 | 3 |
| 10 | 8, 9 | — | 3 |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks → T1-T2 `quick`, T3 `quick`
- **Wave 2**: 2 tasks → T4-T5 `quick`
- **Wave 3**: 5 tasks → T6,T9 `quick`, T7,T10 `unspecified-high`, T8 `deep`

---

## TODOs

- [x] 1. Install streamlit-searchbox and update requirements.txt

  **What to do**:
  - Run `pip install streamlit-searchbox` in project environment
  - Add `streamlit-searchbox` to `requirements.txt`
  - Verify installation by importing in Python REPL

  **Must NOT do**:
  - Do NOT install other ticker search libraries (st-keyup, etc.)
  - Do NOT modify existing dependencies versions

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple dependency installation, straightforward task
  - **Skills**: []
    - No specialized skills needed for basic pip install

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4, 5 (need component)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `requirements.txt` — Current dependency list to append to
  - Official package: `https://pypi.org/project/streamlit-searchbox/` — Installation docs

  **Acceptance Criteria**:
  - [ ] `pip list | grep streamlit-searchbox` → shows installed version
  - [ ] `requirements.txt` contains `streamlit-searchbox` entry
  - [ ] `python -c "from streamlit_searchbox import st_searchbox"` → no import errors

  **QA Scenarios**:
  ```
  Scenario: Verify package installation
    Tool: bash
    Preconditions: Virtual environment activated
    Steps:
      1. Run `pip show streamlit-searchbox`
      2. Check output contains "Name: streamlit-searchbox"
      3. Verify version >= 0.0.1
    Expected Result: Package metadata displayed, no errors
    Failure Indicators: "WARNING: Package(s) not found"
    Evidence: .sisyphus/evidence/task-1-install-verify.txt

  Scenario: Import test
    Tool: bash
    Preconditions: Package installed
    Steps:
      1. Run `python -c "from streamlit_searchbox import st_searchbox; print('OK')"`
      2. Check stdout for "OK"
    Expected Result: "OK" printed, exit code 0
    Evidence: .sisyphus/evidence/task-1-import-test.txt
  ```

  **Evidence to Capture**:
  - [ ] task-1-install-verify.txt (pip show output)
  - [ ] task-1-import-test.txt (import test output)

  **Commit**: YES
  - Message: `chore(deps): add streamlit-searchbox for ticker filtering`
  - Files: `requirements.txt`

---

- [x] 2. Create reusable ticker_search.py component

  **What to do**:
  - Create `components/ticker_search.py` module
  - Implement `search_tickers(query: str) -> List[tuple[str, str]]` function
    - Returns empty list if query empty
    - Filters tickers starting with query (prefix matching, case-insensitive)
    - Limits results to 15 items
  - Use `@st.cache_data(ttl=3600)` for caching ticker list
  - Add `render_ticker_search(key: str, placeholder: str = "Search ticker...") -> str` function
    - Returns selected ticker symbol
    - Uses st_searchbox with search_tickers as search_function
  - Add docstrings to all functions

  **Must NOT do**:
  - Do NOT implement full autocomplete (only prefix filtering)
  - Do NOT call yfinance API on every keystroke (pre-cache ticker list)
  - Do NOT add complex fuzzy matching (just startswith())

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward module creation with clear API
  - **Skills**: []
    - Standard Python/Streamlit, no specialized domain knowledge

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Task 1 (needs streamlit-searchbox installed)

  **References**:
  - Background agent findings: streamlit-searchbox API pattern
  ```python
  st_searchbox(
      search_function: Callable[[str], List[tuple[str, str]]],
      placeholder: str,
      key: str
  )
  ```
  - `legacy/paper_trading.py:228-287` — Existing search_ticker() implementation (adapt this pattern)
  - Research finding: Prefix filtering via `t.upper().startswith(query.upper())`

  **Acceptance Criteria**:
  - [ ] File `components/ticker_search.py` exists
  - [ ] `search_tickers("A")` returns list of tickers starting with "A"
  - [ ] `search_tickers("")` returns empty list
  - [ ] `render_ticker_search("test_key")` returns streamlit component
  - [ ] Ticker list cached for 1 hour (ttl=3600)

  **QA Scenarios**:
  ```
  Scenario: Test prefix filtering
    Tool: bash (python REPL)
    Preconditions: components/ticker_search.py created
    Steps:
      1. python -c "from components.ticker_search import search_tickers; result = search_tickers('A'); print(len(result), result[:3])"
      2. Assert len(result) > 0
      3. Assert all results start with 'A'
    Expected Result: List of 1-15 tickers, all starting with "A"
    Evidence: .sisyphus/evidence/task-2-prefix-filter.txt

  Scenario: Test empty query
    Tool: bash
    Steps:
      1. python -c "from components.ticker_search import search_tickers; print(search_tickers(''))"
    Expected Result: [] (empty list)
    Evidence: .sisyphus/evidence/task-2-empty-query.txt

  Scenario: Test cache
    Tool: bash
    Steps:
      1. python -c "import time; from components.ticker_search import search_tickers; t1=time.time(); search_tickers('A'); t2=time.time(); search_tickers('A'); t3=time.time(); print(f'First: {t2-t1:.3f}s, Cached: {t3-t2:.3f}s')"
      2. Assert cached call < 0.01s
    Expected Result: Second call significantly faster (cached)
    Evidence: .sisyphus/evidence/task-2-cache-test.txt
  ```

  **Evidence to Capture**:
  - [ ] task-2-prefix-filter.txt
  - [ ] task-2-empty-query.txt
  - [ ] task-2-cache-test.txt

  **Commit**: YES
  - Message: `feat(components): add ticker search component with prefix filtering`
  - Files: `components/ticker_search.py`

---

- [x] 3. Add granular DB update methods (update_position, delete_position)

  **What to do**:
  - Add `update_position(user_id: str, ticker: str, quantity: float, buy_price: float) -> bool` to `adapters/db_client.py`
    - Uses Supabase `.update()` with `.eq("user_id", user_id).eq("ticker", ticker)`
    - Returns True on success, False on exception
  - Add `delete_position(user_id: str, ticker: str) -> bool`
    - Uses Supabase `.delete()` with `.eq("user_id", user_id).eq("ticker", ticker)`
    - Returns True on success, False on exception
  - Add docstrings with Args, Returns sections

  **Must NOT do**:
  - Do NOT modify existing save_positions() (keep full-replace available)
  - Do NOT add complex transaction logic (single-row operations only)
  - Do NOT change orders table methods

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward DB method additions following existing patterns
  - **Skills**: []
    - Standard Supabase CRUD, no complex logic

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 6, 7, 8
  - **Blocked By**: None

  **References**:
  - `adapters/db_client.py:45-66` — Existing save_positions() pattern (DELETE + INSERT)
  - `adapters/db_client.py:100-123` — Existing save_order() pattern (single INSERT)
  - Supabase Python docs: `.update()` and `.delete()` syntax
  - Background finding: Current pattern is full-replace only, need row-level operations

  **Acceptance Criteria**:
  - [ ] `update_position()` method exists in DBClient
  - [ ] `delete_position()` method exists in DBClient
  - [ ] Methods return bool (True=success, False=failure)
  - [ ] Methods have proper docstrings

  **QA Scenarios**:
  ```
  Scenario: Update existing position
    Tool: bash (pytest or python script)
    Preconditions: holdings table has test position
    Steps:
      1. Insert test position: user_id="test", ticker="TEST", quantity=100, buy_price=10.0
      2. Call db_client.update_position("test", "TEST", 150, 12.0)
      3. Fetch position: db_client.fetch_positions("test")
      4. Assert quantity=150, buy_price=12.0
    Expected Result: Position updated, returns True
    Evidence: .sisyphus/evidence/task-3-update-position.txt

  Scenario: Delete position
    Tool: bash
    Preconditions: Test position exists
    Steps:
      1. Insert test position
      2. Call db_client.delete_position("test", "TEST")
      3. Fetch positions: should return empty list or exclude TEST
    Expected Result: Position deleted, returns True
    Evidence: .sisyphus/evidence/task-3-delete-position.txt

  Scenario: Error handling (invalid ticker)
    Tool: bash
    Steps:
      1. Call update_position("test", "INVALID_TICKER_XYZ", 100, 10.0)
      2. Assert returns False (no crash)
    Expected Result: Returns False, no exception raised
    Evidence: .sisyphus/evidence/task-3-error-handling.txt
  ```

  **Evidence to Capture**:
  - [ ] task-3-update-position.txt
  - [ ] task-3-delete-position.txt
  - [ ] task-3-error-handling.txt

  **Commit**: YES
  - Message: `feat(db): add granular update/delete methods for positions`
  - Files: `adapters/db_client.py`
  - Pre-commit: `pytest tests/test_db_client.py` (if exists, or skip)

---

- [x] 4. Replace ticker input in Paper Trading tab with ticker search

  **What to do**:
  - Replace `st.text_input` for ticker entry in `ui/paper_trading_tab.py`
  - Import `render_ticker_search` from `components.ticker_search`
  - Pass unique key: `key="paper_trading_ticker"`
  - Store selected ticker in variable for order execution
  - Preserve all existing Paper Trading logic (BUY/SELL, cash tracking, order history)

  **Must NOT do**:
  - Do NOT modify order execution logic
  - Do NOT change cash balance calculations
  - Do NOT alter order persistence to DB

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple UI component replacement, single line change
  - **Skills**: []
    - Standard Streamlit UI modification

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 5)
  - **Blocks**: None
  - **Blocked By**: Task 2 (needs ticker_search component)

  **References**:
  - `ui/paper_trading_tab.py` — Current ticker input location (search for `st.text_input`)
  - `components/ticker_search.py:render_ticker_search()` — Component to use
  - Pattern: Replace `ticker = st.text_input(...)` with `ticker = render_ticker_search(key="paper_trading_ticker")`

  **Acceptance Criteria**:
  - [ ] Paper Trading tab shows ticker search component instead of text input
  - [ ] Selected ticker passes to order execution logic unchanged
  - [ ] BUY/SELL functionality still works with searched tickers
  - [ ] No regressions in order history or cash tracking

  **QA Scenarios**:
  ```
  Scenario: Search and select ticker for order
    Tool: bash (manual Streamlit test)
    Preconditions: App running, Paper Trading tab open
    Steps:
      1. Navigate to Paper Trading tab
      2. Type "AA" in ticker search box
      3. Verify dropdown shows "AAPL", "AAL", etc.
      4. Select "AAPL"
      5. Enter quantity 10, click BUY
      6. Verify order executes (cash deducted, order appears in history)
    Expected Result: Ticker search works, orders execute normally
    Failure Indicators: Dropdown doesn't appear, selected ticker not passed to order logic
    Evidence: .sisyphus/evidence/task-4-ticker-search-ui.png (screenshot)

  Scenario: Empty search behavior
    Tool: bash
    Steps:
      1. Click ticker search box without typing
      2. Verify no dropdown appears (empty query → empty results)
    Expected Result: No dropdown shown on empty input
    Evidence: .sisyphus/evidence/task-4-empty-search.png
  ```

  **Evidence to Capture**:
  - [ ] task-4-ticker-search-ui.png
  - [ ] task-4-empty-search.png

  **Commit**: YES
  - Message: `feat(ui): add ticker search to paper trading tab`
  - Files: `ui/paper_trading_tab.py`

---

- [x] 5. Replace ticker input in AI Prediction tab with ticker search

  **What to do**:
  - Replace `st.text_input` for ticker entry in `ui/prediction_tab.py`
  - Import `render_ticker_search` from `components.ticker_search`
  - Pass unique key: `key="prediction_ticker"`
  - Store selected ticker for prediction request
  - Preserve all existing prediction logic (AI analysis, charts, history)

  **Must NOT do**:
  - Do NOT modify prediction service logic
  - Do NOT change chart rendering
  - Do NOT alter prediction history storage

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Identical to Task 4, simple component swap
  - **Skills**: []
    - Standard Streamlit UI modification

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: None
  - **Blocked By**: Task 2 (needs ticker_search component)

  **References**:
  - `ui/prediction_tab.py` — Current ticker input location
  - `components/ticker_search.py:render_ticker_search()` — Component to use
  - Task 4 implementation — Follow same pattern

  **Acceptance Criteria**:
  - [ ] AI Prediction tab shows ticker search component instead of text input
  - [ ] Selected ticker passes to prediction service unchanged
  - [ ] Predictions generate normally with searched tickers
  - [ ] No regressions in chart display or history

  **QA Scenarios**:
  ```
  Scenario: Search ticker and generate prediction
    Tool: bash (manual Streamlit test)
    Preconditions: App running, AI Prediction tab open
    Steps:
      1. Navigate to AI Prediction tab
      2. Type "GO" in ticker search box
      3. Select "GOOGL"
      4. Click "Get Prediction"
      5. Verify prediction displays (chart, price, reasoning)
    Expected Result: Ticker search works, predictions generate normally
    Evidence: .sisyphus/evidence/task-5-prediction-ticker-search.png

  Scenario: Invalid ticker handling
    Tool: bash
    Steps:
      1. Search and select valid ticker "AAPL"
      2. Manually edit URL/session to inject invalid ticker
      3. Click prediction
      4. Verify error message displays gracefully
    Expected Result: Error handling unchanged from original
    Evidence: .sisyphus/evidence/task-5-invalid-ticker.png
  ```

  **Evidence to Capture**:
  - [ ] task-5-prediction-ticker-search.png
  - [ ] task-5-invalid-ticker.png

  **Commit**: YES
  - Message: `feat(ui): add ticker search to ai prediction tab`
  - Files: `ui/prediction_tab.py`

---

- [x] 6. Fetch Paper Trading positions and current prices

  **What to do**:
  - In `ui/paper_trading_tab.py`, add logic to fetch holdings from DB
  - Use `db_client.fetch_positions(user_id="user123")` 
  - Use `market_data.fetch_current_prices(tickers)` to get live prices
  - Merge holdings with current prices into DataFrame
  - Calculate unrealized P/L: `(current_price - buy_price) * quantity`
  - Display DataFrame columns: ticker, quantity, buy_price, current_price, unrealized_pl

  **Must NOT do**:
  - Do NOT aggregate from orders table (use holdings table directly)
  - Do NOT implement editing logic yet (Task 7)
  - Do NOT add Save button yet (Task 8)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard data fetching and transformation
  - **Skills**: []
    - Basic data manipulation with pandas

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: Task 7
  - **Blocked By**: Task 3 (needs DB methods)

  **References**:
  - `adapters/db_client.py:fetch_positions()` — DB fetch pattern
  - `adapters/market_data.py:fetch_current_prices()` — Price fetching
  - `ui/portfolio_tab.py:36-48` — Similar pattern for Portfolio tab (read-only display)
  - Background finding: holdings table stores positions independently

  **Acceptance Criteria**:
  - [ ] Paper Trading tab displays holdings table (read-only for now)
  - [ ] Table shows: ticker, quantity, buy_price, current_price, unrealized_pl
  - [ ] Current prices fetched from yfinance
  - [ ] Empty state handled (no holdings → no table or empty table message)

  **QA Scenarios**:
  ```
  Scenario: Display holdings with live prices
    Tool: bash (manual Streamlit test)
    Preconditions: holdings table has test positions for user123
    Steps:
      1. Insert test holdings: [("AAPL", 10, 150.0), ("MSFT", 5, 300.0)]
      2. Navigate to Paper Trading tab
      3. Verify table displays with 2 rows
      4. Verify current_price column shows live yfinance data (not 0)
      5. Verify unrealized_pl calculated correctly
    Expected Result: Holdings table displays with live prices
    Evidence: .sisyphus/evidence/task-6-holdings-display.png

  Scenario: Empty holdings state
    Tool: bash
    Preconditions: user123 has no holdings
    Steps:
      1. Clear holdings table for user123
      2. Navigate to Paper Trading tab
      3. Verify graceful empty state (no crash, message or empty table)
    Expected Result: No errors, empty state handled
    Evidence: .sisyphus/evidence/task-6-empty-state.png
  ```

  **Evidence to Capture**:
  - [ ] task-6-holdings-display.png
  - [ ] task-6-empty-state.png

  **Commit**: NO (groups with Task 7)

---

- [x] 7. Render editable holdings table with st.data_editor

  **What to do**:
  - Replace read-only DataFrame display with `st.data_editor`
  - Configure editable columns: quantity, buy_price (ticker read-only)
  - Set `num_rows="dynamic"` to allow row deletion
  - Store edited DataFrame in variable for Save handler (Task 8)
  - Do NOT add `on_change` callback (handled by Save button in Task 8)

  **Must NOT do**:
  - Do NOT implement Save logic yet (Task 8)
  - Do NOT make ticker column editable (primary key)
  - Do NOT make current_price editable (live data)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires careful column configuration and state management
  - **Skills**: []
    - Standard Streamlit data_editor usage

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after Task 6)
  - **Blocks**: Task 8
  - **Blocked By**: Task 6 (needs holdings data fetched)

  **References**:
  - `ui/portfolio_tab.py:36-48` — Existing st.data_editor pattern
  - Streamlit docs: `st.data_editor(df, num_rows="dynamic", disabled=["ticker"])`
  - Background finding: Portfolio uses data_editor with on_change=None, Save button triggers DB write

  **Acceptance Criteria**:
  - [ ] Holdings table editable (quantity, buy_price columns)
  - [ ] Ticker column read-only (primary key protection)
  - [ ] Rows can be deleted via UI
  - [ ] Edits reflected in UI immediately (Streamlit state update)
  - [ ] No Save button yet (added in Task 8)

  **QA Scenarios**:
  ```
  Scenario: Edit quantity and buy_price
    Tool: bash (manual Streamlit test)
    Preconditions: Holdings table displays with data
    Steps:
      1. Navigate to Paper Trading tab
      2. Click quantity cell for AAPL, change from 10 to 15
      3. Click buy_price cell, change from 150.0 to 155.0
      4. Verify UI updates immediately (no Save button yet)
      5. Refresh page → changes LOST (expected, no Save yet)
    Expected Result: Edits reflected in UI, not persisted yet
    Evidence: .sisyphus/evidence/task-7-edit-ui.png

  Scenario: Delete row
    Tool: bash
    Steps:
      1. Click delete icon on AAPL row
      2. Verify row disappears from UI
      3. Refresh page → row reappears (expected, not persisted)
    Expected Result: Row deletion works in UI, not persisted yet
    Evidence: .sisyphus/evidence/task-7-delete-row.png

  Scenario: Ticker column read-only
    Tool: bash
    Steps:
      1. Try to click ticker cell "AAPL"
      2. Verify no edit cursor appears (disabled column)
    Expected Result: Ticker column not editable
    Evidence: .sisyphus/evidence/task-7-readonly-ticker.png
  ```

  **Evidence to Capture**:
  - [ ] task-7-edit-ui.png
  - [ ] task-7-delete-row.png
  - [ ] task-7-readonly-ticker.png

  **Commit**: NO (groups with Task 8)

---

- [x] 8. Implement Save button with granular DB updates

  **What to do**:
  - Add "Save Changes" button below st.data_editor
  - Use `edited_rows`, `added_rows`, `deleted_rows` from data_editor state
  - For edited rows: call `db_client.update_position(user_id, ticker, new_quantity, new_buy_price)`
  - For added rows: call `db_client.save_positions()` with new positions
  - For deleted rows: call `db_client.delete_position(user_id, ticker)`
  - Display success/error messages with `st.success()` / `st.error()`
  - Refresh holdings after save (re-fetch from DB)

  **Must NOT do**:
  - Do NOT use full-replace pattern (use granular update/delete)
  - Do NOT save on every edit (only on button click)
  - Do NOT allow saving invalid data (quantity <= 0, negative price)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex state management, transaction-like logic, error handling critical
  - **Skills**: []
    - Requires careful handling of Streamlit session state and DB operations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after Task 7)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Task 7 (needs editable table)

  **References**:
  - `adapters/db_client.py:update_position()`, `delete_position()` — New methods from Task 3
  - `ui/portfolio_tab.py:36-48` — Save button pattern (but uses full-replace, adapt to granular)
  - Streamlit docs: `st.data_editor` returns dict with `edited_rows`, `added_rows`, `deleted_rows`
  - Background finding: edited_rows format: `{row_index: {col_name: new_value}}`

  **Acceptance Criteria**:
  - [ ] Save button appears below editable table
  - [ ] Clicking Save persists edits to DB via granular updates
  - [ ] Deleted rows removed from DB
  - [ ] Success message displays after save
  - [ ] Holdings refresh after save (show latest DB state)
  - [ ] Validation prevents saving invalid data (quantity <= 0)

  **QA Scenarios**:
  ```
  Scenario: Save edited position
    Tool: bash (manual Streamlit test)
    Preconditions: Holdings table with AAPL position
    Steps:
      1. Edit AAPL quantity: 10 → 20
      2. Edit AAPL buy_price: 150.0 → 160.0
      3. Click "Save Changes"
      4. Verify success message appears
      5. Refresh page (F5)
      6. Verify changes persisted (quantity=20, buy_price=160.0)
    Expected Result: Edits saved to DB, persist across refresh
    Evidence: .sisyphus/evidence/task-8-save-edit.png

  Scenario: Delete position
    Tool: bash
    Steps:
      1. Delete MSFT row from table
      2. Click "Save Changes"
      3. Verify success message
      4. Refresh page
      5. Verify MSFT no longer in holdings
    Expected Result: Deletion persisted to DB
    Evidence: .sisyphus/evidence/task-8-delete-persist.png

  Scenario: Validation error (negative quantity)
    Tool: bash
    Steps:
      1. Edit AAPL quantity to -5
      2. Click "Save Changes"
      3. Verify error message: "Invalid quantity"
      4. Refresh page → original quantity restored
    Expected Result: Invalid data rejected, not saved
    Evidence: .sisyphus/evidence/task-8-validation-error.png

  Scenario: DB error handling
    Tool: bash
    Preconditions: Simulate DB failure (disconnect Supabase or invalid credentials)
    Steps:
      1. Edit position
      2. Click "Save Changes"
      3. Verify error message displays (no crash)
    Expected Result: Graceful error handling
    Evidence: .sisyphus/evidence/task-8-db-error.png
  ```

  **Evidence to Capture**:
  - [ ] task-8-save-edit.png
  - [ ] task-8-delete-persist.png
  - [ ] task-8-validation-error.png
  - [ ] task-8-db-error.png

  **Commit**: YES
  - Message: `feat(ui): add editable holdings table to paper trading with granular DB updates`
  - Files: `ui/paper_trading_tab.py`
  - Pre-commit: Manual UI test (Streamlit app must launch)

---

- [x] 9. Add error handling and user feedback to Paper Trading holdings

  **What to do**:
  - Add try-except blocks around all DB operations in Paper Trading tab
  - Display user-friendly error messages for common failures:
    - Network errors: "Unable to connect to database"
    - Invalid data: "Please enter valid quantity and price"
    - Missing data: "No holdings found"
  - Add loading spinners for fetch operations: `with st.spinner("Loading holdings...")`
  - Add confirmation for destructive actions (optional, if time permits)

  **Must NOT do**:
  - Do NOT remove existing error handling (preserve original error checks)
  - Do NOT add excessive logging (keep it user-facing)
  - Do NOT change error handling in other tabs

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard error handling patterns
  - **Skills**: []
    - Basic Python exception handling

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after Task 8)
  - **Blocks**: Task 10
  - **Blocked By**: Task 8 (needs Save logic implemented)

  **References**:
  - `services/portfolio_service.py` — Error handling patterns (returns dict with success/error)
  - `ui/portfolio_tab.py` — User feedback patterns (st.success, st.error)
  - Background finding: Legacy uses try/except, modern services return success/failure dict

  **Acceptance Criteria**:
  - [ ] All DB operations wrapped in try-except
  - [ ] User-friendly error messages displayed (no raw exceptions)
  - [ ] Loading spinners during fetch operations
  - [ ] No crashes on DB failures

  **QA Scenarios**:
  ```
  Scenario: Network error during fetch
    Tool: bash (simulate by disconnecting network)
    Preconditions: App running
    Steps:
      1. Disconnect network or invalidate Supabase URL
      2. Navigate to Paper Trading tab
      3. Verify error message displays (not raw exception)
      4. Verify app doesn't crash (can still navigate tabs)
    Expected Result: Graceful error handling
    Evidence: .sisyphus/evidence/task-9-network-error.png

  Scenario: Loading spinner during fetch
    Tool: bash
    Steps:
      1. Navigate to Paper Trading tab with large holdings dataset
      2. Observe loading spinner appears briefly
      3. Verify holdings display after spinner disappears
    Expected Result: Loading feedback shown to user
    Evidence: .sisyphus/evidence/task-9-loading-spinner.png
  ```

  **Evidence to Capture**:
  - [ ] task-9-network-error.png
  - [ ] task-9-loading-spinner.png

  **Commit**: YES
  - Message: `fix(ui): add error handling and loading feedback to paper trading`
  - Files: `ui/paper_trading_tab.py`

---

- [x] 10. Write tests for new DB methods and UI flow

  **What to do**:
  - Add test file: `tests/test_db_client_granular.py`
  - Test `update_position()`: success case, failure case, invalid data
  - Test `delete_position()`: success case, failure case, nonexistent ticker
  - Add test file: `tests/test_paper_trading_ui.py` (if feasible)
  - Test holdings fetch and price merge logic
  - Test validation logic (negative quantity, etc.)
  - Run full test suite: `pytest tests/`

  **Must NOT do**:
  - Do NOT remove existing tests
  - Do NOT test UI interactions deeply (Streamlit testing complex, focus on logic)
  - Do NOT test external APIs (mock yfinance, supabase)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding of testing patterns and mocking
  - **Skills**: []
    - Standard pytest, pytest-mock usage

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential, final task)
  - **Blocks**: None (final task)
  - **Blocked By**: Tasks 8, 9 (needs implementation complete)

  **References**:
  - `tests/test_db_client.py` — Existing DB test patterns
  - `tests/test_portfolio_service.py` — Service testing with mocks
  - pytest docs: `@pytest.fixture`, `mocker.patch()`
  - Background finding: Project has pytest + pytest-mock, 16 tests currently

  **Acceptance Criteria**:
  - [ ] Tests for update_position() added (success, failure, edge cases)
  - [ ] Tests for delete_position() added (success, failure, nonexistent)
  - [ ] Tests for holdings validation logic added
  - [ ] All tests pass: `pytest tests/ -v`
  - [ ] Test coverage maintained or improved

  **QA Scenarios**:
  ```
  Scenario: Run new DB method tests
    Tool: bash
    Preconditions: Test files written
    Steps:
      1. Run `pytest tests/test_db_client_granular.py -v`
      2. Verify all tests pass (0 failures)
      3. Check output for test names (test_update_position_success, etc.)
    Expected Result: All new tests pass
    Evidence: .sisyphus/evidence/task-10-test-results.txt

  Scenario: Run full test suite
    Tool: bash
    Steps:
      1. Run `pytest tests/ -v`
      2. Verify 16+ tests pass (original 16 + new tests)
      3. Check for no regressions (existing tests still pass)
    Expected Result: Full suite passes
    Evidence: .sisyphus/evidence/task-10-full-suite.txt
  ```

  **Evidence to Capture**:
  - [ ] task-10-test-results.txt
  - [ ] task-10-full-suite.txt

  **Commit**: YES
  - Message: `test: add tests for granular DB methods and holdings validation`
  - Files: `tests/test_db_client_granular.py`, `tests/test_paper_trading_ui.py` (if created)
  - Pre-commit: `pytest tests/ -v` (must pass)

---

## Final Verification Wave

> Not applicable for this project (no Final Verification wave needed per user's requirements).

---

## Commit Strategy

- **Task 1**: `chore(deps): add streamlit-searchbox for ticker filtering` — requirements.txt
- **Task 2**: `feat(components): add ticker search component with prefix filtering` — components/ticker_search.py
- **Task 3**: `feat(db): add granular update/delete methods for positions` — adapters/db_client.py
- **Task 4**: `feat(ui): add ticker search to paper trading tab` — ui/paper_trading_tab.py
- **Task 5**: `feat(ui): add ticker search to ai prediction tab` — ui/prediction_tab.py
- **Tasks 6-8** (grouped): `feat(ui): add editable holdings table to paper trading with granular DB updates` — ui/paper_trading_tab.py
- **Task 9**: `fix(ui): add error handling and loading feedback to paper trading` — ui/paper_trading_tab.py
- **Task 10**: `test: add tests for granular DB methods and holdings validation` — tests/*.py

---

## Success Criteria

### Verification Commands
```bash
# 1. Check streamlit-searchbox installed
pip show streamlit-searchbox  # Expected: Name: streamlit-searchbox

# 2. Run ticker search component test
python -c "from components.ticker_search import search_tickers; print(search_tickers('A')[:3])"  # Expected: List of tickers starting with A

# 3. Test DB methods
python -c "from adapters.db_client import DBClient; client = DBClient(); print(hasattr(client, 'update_position'), hasattr(client, 'delete_position'))"  # Expected: True True

# 4. Run full test suite
pytest tests/ -v  # Expected: 16+ tests, 0 failures

# 5. Start app and manual verification
streamlit run app.py  # Expected: App launches, no import errors
```

### Final Checklist
- [ ] All "Must Have" present
  - [ ] Editable Paper Trading holdings table
  - [ ] Granular DB updates (row-level UPDATE/DELETE)
  - [ ] Ticker prefix filtering in 2 tabs
  - [ ] Current market price display
- [ ] All "Must NOT Have" absent
  - [ ] Portfolio tab unchanged ✓
  - [ ] No ticker filtering in Portfolio data_editor columns ✓
  - [ ] Orders table structure unchanged ✓
  - [ ] No aggregation from orders ✓
  - [ ] No full autocomplete (only prefix) ✓
- [ ] All tests pass
  - [ ] `pytest tests/ -v` → 0 failures
- [ ] App launches without errors
  - [ ] `streamlit run app.py` → No import errors, UI loads
