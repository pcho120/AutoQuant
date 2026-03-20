# Separate Portfolio and Paper Trading Tables

## Context
- Portfolio tab must use `portfolio` table.
- Paper Trading tab must use `paper_portfolio` table.
- No `holdings`/`orders` scope expansion beyond existing behavior.

## TODOs

- [x] 1. Supabase 테이블 생성 SQL 작성 및 실행 가이드
  - `db/create_tables.sql`에 `portfolio`, `paper_portfolio` 생성 SQL 작성
  - 두 테이블 동일 스키마 + 인덱스 포함

- [x] 2. DBClient 메서드에 table_name 파라미터 추가
  - `adapters/db_client.py`
  - `fetch_positions/save_positions/update_position/delete_position`가 `table_name="portfolio"` 지원

- [x] 3. PortfolioService가 portfolio 테이블 사용
  - `services/portfolio_service.py`에서 `table_name="portfolio"` 전달

- [x] 4. TradingService가 paper_portfolio 테이블 사용
  - `services/trading_service.py`에서 `fetch_positions(..., table_name="paper_portfolio")`

- [x] 5. Paper Trading 탭에서 DBClient 직접 호출 제거
  - `ui/paper_trading_tab.py` DBClient position 호출 모두 `table_name="paper_portfolio"` 명시
  - 대상 호출: `fetch_positions`, `delete_position`, `update_position`, `save_positions`

- [x] 6. 통합 QA - 두 탭의 독립성 검증
  - `tests/test_table_isolation.py` 작성
  - portfolio/paper_portfolio 간 데이터 오염 없음 자동 검증

## Final Verification Wave

- [x] F1. Plan Compliance Audit (oracle)
- [x] F2. Code Quality Review (unspecified-high)
- [x] F3. Real Manual QA (unspecified-high)
- [x] F4. Scope Fidelity Check (deep)

## Success Criteria
- Portfolio 경로는 `portfolio`에만 반영
- Paper Trading 경로는 `paper_portfolio`에만 반영
- 두 탭 데이터 완전 독립
