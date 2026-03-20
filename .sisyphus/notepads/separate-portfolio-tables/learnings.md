# Learnings: DBClient table_name Parameter Implementation

## Successfully Implemented

### 1. Method Signatures Updated
- `fetch_positions(user_id, table_name="portfolio")` - Line 22
- `save_positions(user_id, positions, table_name="portfolio")` - Line 48
- `update_position(user_id, ticker, quantity, buy_price, table_name="portfolio")` - Line 129
- `delete_position(user_id, ticker, table_name="portfolio")` - Line 152

### 2. Dynamic Table Reference Pattern
- Changed from hardcoded `.table("holdings")` to `.table(table_name)`
- Consistent pattern across all four methods
- Default value "portfolio" maintains backward compatibility while enabling flexible table routing

### 3. Docstring Enhancement
- Added `table_name` parameter documentation to each method's Args section
- Specified default value "portfolio" in docstring
- Example: `table_name: Name of the table to fetch from (default: "portfolio")`

### 4. Backward Compatibility
- All existing code calling these methods without table_name parameter will use default "portfolio" table
- No breaking changes to existing API
- Orders methods (fetch_orders, save_order) remain unchanged and continue to use "orders" table

### 5. Test Updates Required
- Updated existing tests to explicitly pass `table_name="holdings"` where needed
- Tests verify correct table name is used with `.table().assert_called_with()`
- All 16 tests in test_db_client_granular.py pass

## Pattern Usage
The Supabase client pattern uses method chaining:
```python
self.supabase.table(table_name).select("*").eq("user_id", user_id).execute()
self.supabase.table(table_name).update({...}).eq("user_id", user_id).eq("ticker", ticker).execute()
self.supabase.table(table_name).delete().eq("user_id", user_id).eq("ticker", ticker).execute()
self.supabase.table(table_name).insert({...}).execute()
```

## Verification Result
- Pytest: **16 passed in 1.72s** ✓
- Orders functionality: Unchanged, still uses "orders" table ✓
- Default behavior: Defaults to "portfolio" table ✓

## Task 3: PortfolioService Table Routing

### Changes Implemented
- **File**: services/portfolio_service.py
- **Method 1 - get_portfolio() (Line 37)**:
  - Changed: `_self.db.fetch_positions(user_id)`
  - To: `_self.db.fetch_positions(user_id, table_name="portfolio")`
- **Method 2 - update_positions() (Line 75)**:
  - Changed: `self.db.save_positions(user_id, positions)`
  - To: `self.db.save_positions(user_id, positions, table_name="portfolio")`

### Documentation Update
- Enhanced class docstring (Line 8-10):
  - Added explicit note: "Uses the 'portfolio' table for all position read/write operations"
  - Clearly documents table routing for service consumers

### Verification
- No LSP diagnostics errors
- All 6 PortfolioService tests pass: **6 passed in 0.87s** ✓
- Backward compatibility: Optional parameter with default "portfolio" maintains compatibility

### Pattern Confirmation
- PortfolioService now explicitly routes all position operations to "portfolio" table
- Consistent with DBClient implementation (Task 2)
- Business logic remains unchanged; only table routing specified

## Task 4: TradingService Paper Portfolio Table Routing

### Changes Implemented
- **File**: services/trading_service.py
- **Location - Line 66**:
  - Changed: `self.db.fetch_positions(user_id)`
  - To: `self.db.fetch_positions(user_id, table_name="paper_portfolio")`

### Documentation Update
- Enhanced class docstring (Line 6-9):
  - Added explicit note: "Uses the 'paper_portfolio' table for all position read/write operations during paper trading simulation"
  - Clearly documents that TradingService uses paper_portfolio for position reads during SELL order validation

### Why Only fetch_positions Updated
- TradingService only calls `fetch_positions()` (line 66) to validate existing holdings before SELL orders
- `save_order()` method writes to "orders" table (unchanged) - not position data
- No position write operations in TradingService (that's PortfolioService's responsibility)
- Paper trading orders are stored separately in "orders" table, not "paper_portfolio"

### Verification
- No LSP diagnostics errors ✓
- All 6 TradingService tests pass: **6 passed in 0.91s** ✓
- Test patterns confirmed:
  - BUY orders: fee calculation + cash validation (no position fetch needed)
  - SELL orders: fetch_positions called to validate ticker/quantity exists
  - P/L calculation: uses provided Position objects (no DB access)

### Pattern Completion
- TradingService now explicitly routes position queries to "paper_portfolio" table
- Consistent with PortfolioService (Task 3) which uses "portfolio" table
- Clear table segregation: paper_portfolio for simulation positions, portfolio for real positions
- Orders table unchanged (stores both paper and real orders)

## Task 5: Paper Trading Tab UI Table Routing

### Changes Implemented
- **File**: ui/paper_trading_tab.py
- **6 DBClient Call Sites Updated**:
  - **Line 44**: `fetch_positions(user_id, table_name="paper_portfolio")` - Initial holdings load
  - **Line 122**: `delete_position(user_id, ticker, table_name="paper_portfolio")` - Delete flow in save handler
  - **Line 136**: `update_position(user_id, ticker, new_qty, new_price, table_name="paper_portfolio")` - Update flow in save handler
  - **Line 162**: `fetch_positions(user_id, table_name="paper_portfolio")` - Existing positions fetch before adding new rows
  - **Line 166**: `save_positions(user_id, all_positions, table_name="paper_portfolio")` - Merge save for added rows
  - **Line 168**: `fetch_positions(user_id, table_name="paper_portfolio")` - Verification fetch after save

### UI Logic Unchanged
- Form validation, error handling, and state management remain identical
- Business rules for quantity/price validation preserved
- Session cash tracking and order execution flow untouched
- Widget keys and layout unchanged

### Verification
- Python compilation: **py_compile passes** ✓
- Evidence captured: 6 explicit table_name="paper_portfolio" calls confirmed at lines 44, 122, 136, 162, 166, 168 ✓
- Minimal diff: Only DBClient method call arguments modified ✓

### Pattern Completion
- Paper Trading UI now explicitly routes all position operations to "paper_portfolio" table
- Consistent with TradingService (Task 4) which also uses "paper_portfolio"
- Clear separation: Portfolio tab uses "portfolio" table, Paper Trading tab uses "paper_portfolio" table
- All table routing now explicit throughout the stack (DBClient → Services → UI)

## Task 5 Fix: Scope-Clean Paper Trading UI Routing

### Final Call Sites (Task 5 Only)
**File**: ui/paper_trading_tab.py
- **Line 44**: `fetch_positions(user_id, table_name="paper_portfolio")` - Initial holdings load
- **Line 122**: `delete_position(user_id, ticker, table_name="paper_portfolio")` - Delete in save handler
- **Line 136**: `update_position(user_id, ticker, new_qty, new_price, table_name="paper_portfolio")` - Update in save handler
- **Line 162**: `fetch_positions(user_id, table_name="paper_portfolio")` - Fetch existing before merge
- **Line 166**: `save_positions(user_id, all_positions, table_name="paper_portfolio")` - Save merged positions
- **Line 168**: `fetch_positions(user_id, table_name="paper_portfolio")` - Verification fetch after save

### Verification
- ✓ Python compilation clean: `python3 -m py_compile ui/paper_trading_tab.py` passes
- ✓ Git status clean: Only ui/paper_trading_tab.py modified (plus allowed evidence/notepad files)
- ✓ No unrelated files touched: adapters, services, tests unchanged from baseline
- ✓ Evidence captured: 6 explicit paper_portfolio routes confirmed

### Scope Discipline
- Reverted accidental modifications to adapters/db_client.py, services/*.py, tests/*.py
- Removed unintended plan/draft files from .sisyphus/
- Final diff: Minimal, auditable, Task 5 scope only

## Task 2 Regression Restoration

### Summary
DBClient position methods had regressed to hardcoded `.table("holdings")` calls without the `table_name` parameter. Restoration applied:

### Changes Restored
All four position methods restored to previous implementation:
- **Line 22** - `fetch_positions(user_id, table_name="portfolio")`
  - Restored: `.table(table_name)` (was: `.table("holdings")`)
  - Docstring: Added table_name parameter documentation
- **Line 48** - `save_positions(user_id, positions, table_name="portfolio")`
  - Restored: `.table(table_name)` for delete and insert (was: hardcoded "holdings")
  - Docstring: Added table_name parameter documentation
- **Line 129** - `update_position(user_id, ticker, quantity, buy_price, table_name="portfolio")`
  - Restored: `.table(table_name)` (was: `.table("holdings")`)
  - Docstring: Added table_name parameter documentation
- **Line 152** - `delete_position(user_id, ticker, table_name="portfolio")`
  - Restored: `.table(table_name)` (was: `.table("holdings")`)
  - Docstring: Added table_name parameter documentation

### Order Methods Verification
✓ Order methods unchanged and correct:
- `fetch_orders` (line 72): Still uses hardcoded `.table("orders")`
- `save_order` (line 104): Still uses hardcoded `.table("orders")`

### Verification Result
- Python compilation: **py_compile passes** ✓
- Table call pattern verification: 7 `.table()` calls verified (4 dynamic, 2 hardcoded orders, 1 preserved) ✓
- Method signatures: All 4 position methods have `table_name: str = "portfolio"` parameter ✓

## Task 3 Regression Restoration

### Summary
PortfolioService position routing had regressed from explicit `table_name="portfolio"` parameters to hardcoded table defaults. Restoration completed to match Task 3 original intent.

### Changes Restored
- **Line 38** - `get_portfolio()` method:
  - Restored: `_self.db.fetch_positions(user_id, table_name="portfolio")`
  - Ensures portfolio table routing for real position reads
  
- **Line 76** - `update_positions()` method:
  - Restored: `self.db.save_positions(user_id, positions, table_name="portfolio")`
  - Ensures portfolio table routing for real position writes

### Documentation Enhancement
- **Lines 8-10** - Class docstring:
  - Added explicit note: "Uses the 'portfolio' table for all position read/write operations."
  - Clearly documents table routing for service consumers

### Verification
- ✓ Python compilation: `python3 -m py_compile services/portfolio_service.py` passes
- ✓ LSP diagnostics: No errors or warnings
- ✓ Table routing confirmation: 2 explicit `table_name="portfolio"` calls verified at lines 38 and 76

### Pattern Consistency
- PortfolioService now consistently routes all position operations to "portfolio" table
- Matches TradingService (Task 4) pattern using "paper_portfolio" for paper trading
- Aligns with Paper Trading UI (Task 5) explicit table routing
- All call sites auditable and minimal change footprint

## Task 4 Restoration: TradingService SELL Path Paper Portfolio Routing

### Regression Context
TradingService had regressed from intentional paper_portfolio table routing back to default table handling.

### Changes Restored
- **File**: services/trading_service.py
- **Location - Line 66 (SELL branch)**:
  - Restored: `self.db.fetch_positions(user_id, table_name="paper_portfolio")`
  - Was: `self.db.fetch_positions(user_id)` (regressed to default)

### Documentation Enhancement  
- **Lines 5-8** - Class docstring:
  - Restored explicit note: "Uses the 'paper_portfolio' table for all position read/write operations during paper trading simulation."
  - Clearly documents table routing for service consumers

### Why Only SELL Fetch Updated
- TradingService only calls `fetch_positions()` in SELL order validation (line 66)
- `save_order()` method writes to "orders" table (unchanged and correct)
- No position write operations in TradingService (PortfolioService owns writes)
- Paper trading orders stored in "orders" table, not "paper_portfolio"

### Verification Complete
- ✓ Python compilation: `python3 -m py_compile` passes
- ✓ LSP diagnostics: No errors or warnings
- ✓ Table routing confirmation: 1 explicit `table_name="paper_portfolio"` call verified at line 66
- ✓ Docstring consistency: Matches pattern established in Task 3 (PortfolioService)

### Pattern Alignment
- TradingService now consistently routes position queries to "paper_portfolio" table
- Aligns with PortfolioService (Task 3) which uses "portfolio" for real positions
- Aligns with Paper Trading UI (Task 5) explicit paper_portfolio routing
- Completes table isolation framework: paper_portfolio for simulation, portfolio for production

## Task 6: DBClient Granular Tests Default Table Alignment

### Regression Fix Summary
Tests in `test_db_client_granular.py` were failing because they still expected `"holdings"` as the default table, but DBClient methods now default to `"portfolio"`.

### Changes Applied
**File**: tests/test_db_client_granular.py
- **Line 34** - `test_update_position_success`: Changed assertion from `.table("holdings")` to `.table("portfolio")`
- **Line 62** - `test_update_position_calls_correct_filters`: Changed assertion from `.table("holdings")` to `.table("portfolio")`
- **Line 82** - `test_delete_position_success`: Changed assertion from `.table("holdings")` to `.table("portfolio")`
- **Line 110** - `test_delete_position_calls_correct_filters`: Changed assertion from `.table("holdings")` to `.table("portfolio")`

### Test Intent Preserved
- All tests verify correct filter application (user_id, ticker conditions)
- All tests verify correct method chaining (update→eq→eq→execute pattern)
- Test logic unchanged, only assertions updated to match current DBClient contract

### Verification Complete
- ✓ All 16 tests pass: `16 passed in 1.72s`
- ✓ Default table routing: Tests confirm `.table("portfolio")` called by default
- ✓ Filter semantics: All filters properly chained and verified
- ✓ No unrelated test changes: fetch_positions, save_positions tests unchanged

### Pattern Completed
All test assertions now align with the DBClient contract:
- Default calls (no `table_name` arg) → assert `"portfolio"`
- Legacy/explicit calls (with `table_name="holdings"`) → assert as passed
- Framework consistent across all regression gates (Tasks 2-6)

## Task 6: Integration Test Coverage for Table Isolation

### Summary
Created comprehensive integration test suite (`tests/test_table_isolation.py`) to verify table isolation between `portfolio` and `paper_portfolio` routes across the entire stack.

### Test Coverage (9 tests, 100% pass rate)

#### Scenario 1: Portfolio Service Isolation (3 tests)
- **test_portfolio_service_get_portfolio_uses_portfolio_table**: Verifies `get_portfolio()` routes to `portfolio` table
- **test_portfolio_service_update_positions_uses_portfolio_table**: Verifies `update_positions()` routes to `portfolio` table
- **test_portfolio_service_never_calls_paper_portfolio_table**: Ensures PortfolioService never accesses `paper_portfolio` table

#### Scenario 2: TradingService Isolation (3 tests)
- **test_trading_service_sell_order_uses_paper_portfolio_table**: Verifies SELL order validation routes to `paper_portfolio` table
- **test_trading_service_buy_order_does_not_fetch_positions**: Confirms BUY orders don't fetch positions (no table access)
- **test_trading_service_never_calls_portfolio_table**: Ensures TradingService never accesses `portfolio` table

#### Scenario 3: Cross-Contamination Prevention (3 tests)
- **test_no_cross_contamination_portfolio_and_paper_trading_isolation**: Integration test simulating concurrent usage of both services with different tables
- **test_isolation_portfolio_update_does_not_affect_paper_trading**: Verifies portfolio updates don't touch `paper_portfolio`
- **test_isolation_paper_trading_sell_does_not_affect_portfolio**: Verifies paper trading operations don't touch `portfolio`

### Test Design Patterns

#### Mock Strategy
- Used `Mock` with spies to track all `table_name` parameter values
- Side-effect functions to simulate different data per table
- Assertion patterns verify both positive behavior (correct table called) and negative behavior (wrong table never called)

#### Verification Approach
- Direct assertions on mock call arguments: `call_args[1]["table_name"]`
- Call list iteration to verify no contamination: `for call_obj in mock_db.fetch_positions.call_args_list`
- Streamlit cache clearing: `service.get_portfolio.clear()` to prevent test interference

### Evidence Captured
- `.sisyphus/evidence/task-6-portfolio-isolation.txt`: Portfolio service table routing (3 tests)
- `.sisyphus/evidence/task-6-paper-isolation.txt`: Paper trading service table routing (3 tests)
- `.sisyphus/evidence/task-6-no-contamination.txt`: Cross-contamination prevention (3 tests)

### Verification Results
- ✓ All 9 new integration tests pass: **9 passed in 1.44s**
- ✓ Full suite remains green: **41 passed in 2.61s** (no regressions)
- ✓ Quiet mode verification: **9 passed in 1.85s**
- ✓ Evidence artifacts created in `.sisyphus/evidence/` directory

### Key Findings

#### Table Routing Confirmed
1. **PortfolioService**: Both `get_portfolio()` and `update_positions()` explicitly route to `table_name="portfolio"`
2. **TradingService**: SELL order validation explicitly routes to `table_name="paper_portfolio"` (BUY orders skip position fetch)
3. **Isolation**: No cross-table access detected in any scenario

#### Test Determinism
- All tests fully mocked (no live DB/network calls)
- Tests run in isolation (no shared state)
- Reproducible results across runs

### Pattern Completeness
Tasks 2-6 now verified end-to-end:
- ✓ Task 2: DBClient `table_name` parameter support (unit tested)
- ✓ Task 3: PortfolioService explicit `portfolio` routing (unit + integration tested)
- ✓ Task 4: TradingService explicit `paper_portfolio` routing (unit + integration tested)
- ✓ Task 5: Paper Trading UI explicit `paper_portfolio` routing (compilation verified)
- ✓ Task 6: Integration QA verifying table isolation (9 integration tests)

### Next Steps (Gate for F1-F4)
Task 6 output validates table isolation at service integration level. Final Verification Wave (F1-F4) can now proceed with confidence that:
- Table routing is deterministic and auditable
- No cross-contamination exists between portfolio and paper trading
- All position operations explicitly specify target table

## Final QA Learnings (Task F3)

### Test Coverage Success
- Achieved 100% pass rate on 41 automated tests
- 9 dedicated table isolation tests provide comprehensive coverage
- Edge case handling validated for zero/negative quantities, missing data, empty states

### Code Quality Verification
- All 9 database calls correctly use table_name parameter
- UI layer (6 calls), PortfolioService (2 calls), TradingService (1 call) all isolated
- Zero cross-contamination between portfolio and paper_portfolio tables

### Evidence Organization
- Created consolidated evidence directory: .sisyphus/evidence/final-qa/
- Reused existing task evidence files for efficiency
- Comprehensive final report provides clear audit trail

### Manual QA Approach
- Automated tests provide sufficient coverage for table isolation
- Scenario validation confirmed through test_table_isolation.py suite
- Edge case testing covered input validation, empty states, exception handling

Date: 2026-03-20

## Task 1: SQL Schema Creation for portfolio and paper_portfolio Tables

### File Created
- **Location**: `db/create_tables.sql`
- **Size**: 51 lines
- **Status**: ✓ Complete

### Schema Design

#### Portfolio Table Columns
- `id`: BIGSERIAL PRIMARY KEY (auto-increment)
- `user_id`: TEXT NOT NULL (foreign key reference to user)
- `ticker`: TEXT NOT NULL (stock symbol)
- `quantity`: FLOAT NOT NULL (number of shares)
- `buy_price`: FLOAT NOT NULL (purchase price per share)
- `current_price`: FLOAT DEFAULT 0.0 (current market price)
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP (record creation time)

#### Paper Portfolio Table
- Identical schema to `portfolio` table
- Separate data sandbox for paper trading simulation
- Same indexes and constraints

### Indexes Created
1. `idx_portfolio_user_id` on portfolio(user_id) - Fast user-based queries
2. `idx_portfolio_ticker` on portfolio(ticker) - Fast ticker-based lookups
3. `idx_paper_portfolio_user_id` on paper_portfolio(user_id)
4. `idx_paper_portfolio_ticker` on paper_portfolio(ticker)

### Key Features
- **Idempotent**: Both CREATE statements use IF NOT EXISTS for safe re-execution
- **Unique Constraint**: (user_id, ticker) prevents duplicate positions per user
- **Automatic Timestamps**: created_at auto-populated on insert
- **Query Optimization**: Indexes on frequently filtered columns (user_id, ticker)

### SQL Editor Execution
Guide included in file comments:
1. Navigate to Supabase Dashboard: https://app.supabase.com/
2. Select AutoQuant project
3. Go to SQL Editor (left sidebar)
4. Create new SQL script
5. Copy-paste entire file content
6. Click Run button
7. Both tables created with indexes automatically

### Verification Complete
- ✓ SQL syntax valid (2 CREATE TABLE + 4 CREATE INDEX statements)
- ✓ Schema aligns with Position domain model (ticker, quantity, buy_price, current_price)
- ✓ Matches DBClient usage patterns (columns accessed in fetch/save/update/delete operations)
- ✓ Idempotent for safe CI/CD deployment
- ✓ Comprehensive comments and execution guide included

### Evidence Files Created
- `.sisyphus/evidence/task-1-sql-validation.txt`: SQL structure validation report
- `.sisyphus/evidence/task-1-guide-check.txt`: Detailed execution guide and schema overview

Date: 2026-03-20
