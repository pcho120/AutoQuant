# AutoQuant 리팩토링: Streamlit 유지 + 아키텍처 개선

## TL;DR

> **Quick Summary**: AutoQuant를 Streamlit 기반으로 유지하되, 비즈니스 로직을 UI에서 분리하여 유지보수성과 성능을 대폭 개선. Edit state loss 버그 해결, 3-5배 성능 향상, AI 가격 예측 기능 추가.
> 
> **Deliverables**:
> - Domain models (순수 Python 클래스)
> - Adapters (병렬 API 호출, DB/News 래퍼)
> - Services (비즈니스 로직 + 캐싱)
> - UI layer (Streamlit 코드만: Portfolio, Trading, Prediction, **Settings** 탭)
> - AI Price Prediction 기능 (뉴스 + 기술적 지표 기반)
> - Legacy 코드 제거 및 테스트
> 
> **Estimated Effort**: Large (70시간 총 작업 시간)
> **Parallel Execution**: YES - 6 waves
> **Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

---

## Context

### Original Request
사용자가 Portfolio 탭 테이블에서 값을 수정하는 중 화면이 새로고침되어 입력한 값이 저장 전에 사라지는 문제 발생. Streamlit vs FastAPI+React 전환 여부 결정 필요. AI 코드 생성 시 불필요하게 긴 코드(중복 변수, 함수, 클래스) 방지 필요. **캐시 관리를 위한 Settings 탭 추가 요청 (캐시 삭제 버튼)**.

### Interview Summary
**Key Discussions**:
- Edit state loss 원인: Streamlit rerun 모델 + 매 render마다 price fetch
- Framework 선택: Streamlit 유지 결정 (현재 규모에 적합, FastAPI 전환은 premature optimization)
- 3가지 목표 기능: Portfolio Tracking (90% 완료), Paper Trading (100% 완료), AI Price Prediction (0% → 구현 예정)
- Performance: 캐싱 없음, 순차 API 호출 → 3-5배 개선 가능
- Code quality: AI 생성 코드의 불필요한 verbosity 방지 규칙 필요

**Research Findings**:
- 현재 코드 953줄, 107개 `st.*` 호출, 캐싱 데코레이터 0개
- 모든 모듈이 Streamlit에 강하게 결합 (UI + 로직 혼재)
- yfinance 병렬 호출 시 Issue #2557 주의 (`Ticker().history()` 사용, `download()` 피하기)
- 5개 티커 순차 조회: 2.5초 → 병렬 시 0.5-0.7초 (4-5배 개선)

### Metis Review
**Identified Gaps** (addressed):
- 성능 최적화 전략 구체화 필요 → TTL 기반 캐싱, ThreadPoolExecutor 병렬 처리 추가
- AI 코드 bloat 방지 규칙 필요 → YAGNI/DRY/KISS 10가지 규칙 명시
- Test infrastructure 확인 필요 → pytest 설정 추가 예정
- Phase별 중단/재개 전략 필요 → Git 커밋 단위 체크포인트 전략 수립

---

## Work Objectives

### Core Objective
Streamlit 기반을 유지하면서 아키텍처를 "monolithic app"에서 "thin UI shell over services"로 전환하여 유지보수성, 성능, 확장성을 개선.

### Concrete Deliverables
- `domain/` - 순수 Python 도메인 모델 (ticker.py, position.py, prediction.py)
- `adapters/` - 외부 API 래퍼 (market_data.py, db_client.py, news_provider.py)
- `services/` - 비즈니스 로직 (portfolio_service.py, trading_service.py, prediction_service.py)
- `ui/` - Streamlit UI 레이어 (portfolio_tab.py, paper_trading_tab.py, prediction_tab.py, **settings_tab.py**)
- `tests/` - 서비스 레이어 단위 테스트 (최소 8개)
- `legacy/` - 기존 코드 이동 (portfolio.py, chart.py, paper_trading.py)
- 업데이트된 `app.py` - 의존성 주입 및 **4개 탭** 라우팅 (Portfolio, Trading, Prediction, **Settings**)

### Definition of Done
- [ ] `bun test` 또는 `pytest` 실행 시 모든 테스트 통과
- [ ] `streamlit run app.py` 실행 시 3개 탭 모두 정상 동작
- [ ] Portfolio 편집 → 저장 → 새로고침 시 값 유지 확인 (edit state loss 해결)
- [ ] 5개 티커 가격 조회 < 1초 확인 (병렬 처리)
- [ ] AI Prediction 기능에서 예측 결과 표시 확인
- [ ] `domain/`, `services/`, `adapters/`에 `import streamlit` 없음 확인 (캐싱 제외)

### Must Have
- Edit state loss 완전 해결 (조건부 refresh 적용)
- 병렬 API 호출 구현 (ThreadPoolExecutor)
- 캐싱 전략 적용 (TTL 기반)
- AI 가격 예측 기능 (뉴스 감정 + 기술적 지표)
- Anti-bloat 코딩 규칙 준수 (YAGNI/DRY/KISS)

### Must NOT Have (Guardrails)
- FastAPI 또는 다른 프레임워크 전환 (Streamlit 유지)
- 과도한 추상화 (2회 미만 사용 시 추출 금지)
- 불필요한 중간 변수 (단일 사용 변수)
- 명백한 코드에 대한 주석 ("Fetch data", "Get value" 등)
- 프로덕션 코드에 `console.log`, `print()` (에러 핸들링 제외)
- Magic number (상수로 추출 필수)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (pytest 설정 예정)
- **Automated tests**: Tests-after (구현 후 테스트 추가)
- **Framework**: pytest
- **Test setup task**: Phase 6에 포함

### QA Policy
모든 task는 agent-executed QA scenarios 포함 필수.
Evidence는 `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`에 저장.

- **UI (Portfolio, Trading, Prediction tabs)**: Playwright 사용 - 브라우저 실행, 상호작용, DOM 검증, 스크린샷
- **CLI 명령**: Bash (curl, bun test, pytest)
- **Service 로직**: Python REPL 또는 pytest

---

## Execution Strategy

### Parallel Execution Waves

> 각 Phase는 순차적이지만, Phase 내 파일 생성은 병렬 가능.
> 중단/재개: 파일 단위 또는 함수 단위로 커밋하여 체크포인트 생성.

```
Wave 1 (Phase 1 - Domain Models):
├── Task 1: domain/ticker.py [quick]
├── Task 2: domain/position.py [quick]
└── Task 3: domain/prediction.py [quick]

Wave 2 (Phase 2 - Adapters):
├── Task 4: adapters/market_data.py (병렬 API 구현) [unspecified-high]
├── Task 5: adapters/db_client.py [quick]
└── Task 6: adapters/news_provider.py (스텁) [quick]

Wave 3 (Phase 3 - Services):
├── Task 7: services/portfolio_service.py (캐싱 포함) [deep]
├── Task 8: services/trading_service.py [unspecified-high]
└── Task 9: services/prediction_service.py (스텁) [quick]

Wave 4 (Phase 4 - UI Layer):
├── Task 10: ui/portfolio_tab.py (조건부 refresh) [visual-engineering]
├── Task 11: ui/paper_trading_tab.py [visual-engineering]
└── Task 12: ui/prediction_tab.py (스텁) [visual-engineering]

Wave 5 (Phase 5 - AI Prediction):
├── Task 13: adapters/news_provider.py 완성 (NewsAPI 통합) [unspecified-high]
├── Task 14: services/prediction_service.py - 기술적 지표 [deep]
├── Task 15: services/prediction_service.py - AI 모델 (규칙 기반) [ultrabrain]
└── Task 16: ui/prediction_tab.py 완성 [visual-engineering]

Wave 6 (Phase 6 - Cleanup & Testing):
├── Task 17: Legacy 코드 이동 [quick]
├── Task 18: app.py 업데이트 (의존성 주입) [quick]
├── Task 19: pytest 설정 및 테스트 작성 [unspecified-high]
└── Task 20: 통합 테스트 및 문서화 [unspecified-high]

Critical Path: Task 1-3 → Task 4-6 → Task 7-9 → Task 10-12 → Task 13-16 → Task 17-20
Parallel Speedup: 파일 단위 병렬 가능 (같은 Wave 내)
Max Concurrent: 3 (Wave당)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1-3 | - | 4-6 |
| 4-6 | 1-3 | 7-9 |
| 7-9 | 4-6 | 10-12A |
| 10-12A | 7-9 | 17-18 |
| 13 | 6 | 14-15 |
| 14-15 | 9, 13 | 16 |
| 16 | 12, 15 | 20 |
| 17-18 | 10-12A | 19-20 |
| 19-20 | 17-18 | - |

### Agent Dispatch Summary

- **Wave 1**: Task 1-3 → `quick` (3개 파일, 각 10-20분)
- **Wave 2**: Task 4 → `unspecified-high`, Task 5-6 → `quick`
- **Wave 3**: Task 7 → `deep`, Task 8 → `unspecified-high`, Task 9 → `quick`
- **Wave 4**: Task 10-12A → `visual-engineering` (Portfolio, Trading, Prediction tabs) + `quick` (Settings tab)
- **Wave 5**: Task 13 → `unspecified-high`, Task 14 → `deep`, Task 15 → `ultrabrain`, Task 16 → `visual-engineering`
- **Wave 6**: Task 17-18 → `quick`, Task 19-20 → `unspecified-high`

---

## TODOs

### Wave 1: Domain Models (Phase 1)

- [x] 1. domain/ticker.py 생성

  **What to do**:
  - `Sector` Enum 생성 (TECH, FINANCE, HEALTHCARE, ENERGY, CONSUMER, INDUSTRIAL, UTILITIES, REAL_ESTATE, UNKNOWN)
  - `RiskLevel` Enum 생성 (LOW, MEDIUM, HIGH)
  - `Ticker` dataclass 생성 (symbol, sector, risk_level)
  - `__str__` 메서드 구현

  **Must NOT do**:
  - `import streamlit` 금지
  - 불필요한 헬퍼 함수 추가 금지
  - 과도한 주석 금지

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 단순 데이터 클래스 정의, 외부 의존성 없음
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 2, 3과 병렬)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 4-6
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:51-84` - domain/ticker.py 코드 예시
  - Anti-bloat 규칙: `.sisyphus/drafts/portfolio-editor-refresh-loss.md:615-880`

  **Acceptance Criteria**:
  - [ ] `domain/ticker.py` 파일 존재
  - [ ] `Sector` Enum 8개 값 + UNKNOWN
  - [ ] `RiskLevel` Enum 3개 값
  - [ ] `Ticker` dataclass 3개 필드
  - [ ] `import streamlit` 없음 확인: `grep -r "import streamlit" domain/ticker.py` → 빈 결과

  **QA Scenarios**:
  ```
  Scenario: Ticker 객체 생성 및 출력
    Tool: Bash (Python REPL)
    Steps:
      1. cd /home/pcho/projects/AutoQuant
      2. python3 -c "from domain.ticker import Ticker, Sector, RiskLevel; t = Ticker('AAPL', Sector.TECH, RiskLevel.HIGH); print(t)"
      3. 출력 확인: "AAPL (technology, high)"
    Expected Result: 정확한 문자열 출력
    Evidence: .sisyphus/evidence/task-1-ticker-creation.txt

  Scenario: Enum 값 검증
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from domain.ticker import Sector; print(len(Sector))"
      2. 출력 확인: "9" (8개 섹터 + UNKNOWN)
    Expected Result: Sector Enum 9개 값
    Evidence: .sisyphus/evidence/task-1-enum-validation.txt
  ```

  **Evidence to Capture**:
  - [ ] task-1-ticker-creation.txt
  - [ ] task-1-enum-validation.txt

  **Commit**: YES
  - Message: `feat(domain): add Ticker, Sector, RiskLevel models`
  - Files: `domain/ticker.py`, `domain/__init__.py`

---

- [x] 2. domain/position.py 생성

  **What to do**:
  - `Position` dataclass 생성 (ticker, quantity, buy_price, current_price)
  - `@property` 메서드: market_value, pnl_dollars, pnl_percent
  - `Portfolio` dataclass 생성 (positions: List[Position], cash: float)
  - `@property` 메서드: total_value, invested_value
  - `to_dataframe()` 메서드 (pandas import는 메서드 내부에서만)
  - `Order` dataclass 생성 (ticker, action, quantity, price, timestamp, fee)
  - `@property` 메서드: total_cost

  **Must NOT do**:
  - pandas를 모듈 레벨에서 import (to_dataframe 내부에서만)
  - 중간 변수 남발 (예: `value = market_value; return value`)
  - 불필요한 validation 로직 (service 레이어에서 처리)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 데이터 클래스 + 간단한 계산 로직
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 1, 3과 병렬)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 4-6
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:86-157` - domain/position.py 코드 예시
  - Anti-bloat Rule 1: `.sisyphus/drafts/portfolio-editor-refresh-loss.md:642-655` - 단일 사용 변수 금지

  **Acceptance Criteria**:
  - [ ] `Position` dataclass 3개 @property 메서드
  - [ ] `Portfolio` dataclass 2개 @property 메서드
  - [ ] `to_dataframe()` 메서드 pandas import 로컬
  - [ ] `Order` dataclass 1개 @property 메서드
  - [ ] Zero division 방지: `pnl_percent`에서 buy_price == 0 처리

  **QA Scenarios**:
  ```
  Scenario: Position P/L 계산
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from domain.position import Position; p = Position('AAPL', 10, 150, 160); print(f'P/L: ${p.pnl_dollars}, {p.pnl_percent:.2f}%')"
      2. 출력 확인: "P/L: $100.0, 6.67%"
    Expected Result: 정확한 P/L 계산
    Evidence: .sisyphus/evidence/task-2-position-pnl.txt

  Scenario: Portfolio 총 가치 계산
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from domain.position import Position, Portfolio; p1 = Position('AAPL', 10, 150, 160); p2 = Position('GOOGL', 5, 100, 120); portfolio = Portfolio([p1, p2], cash=500); print(f'Total: ${portfolio.total_value}')"
      2. 출력 확인: "Total: $2700.0" (1600 + 600 + 500)
    Expected Result: 정확한 합계
    Evidence: .sisyphus/evidence/task-2-portfolio-total.txt

  Scenario: DataFrame 변환
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from domain.position import Position, Portfolio; p = Position('AAPL', 10, 150, 160); portfolio = Portfolio([p], 0); df = portfolio.to_dataframe(); print(df.columns.tolist())"
      2. 출력 확인: ['Ticker', 'Quantity', 'Buy Price', 'Current Price', 'Mkt Value', 'P/L ($)', 'P/L (%)']
    Expected Result: 7개 컬럼
    Evidence: .sisyphus/evidence/task-2-dataframe-columns.txt
  ```

  **Evidence to Capture**:
  - [ ] task-2-position-pnl.txt
  - [ ] task-2-portfolio-total.txt
  - [ ] task-2-dataframe-columns.txt

  **Commit**: YES
  - Message: `feat(domain): add Position, Portfolio, Order models`
  - Files: `domain/position.py`, `domain/__init__.py`

---

- [x] 3. domain/prediction.py 생성

  **What to do**:
  - `PredictionRequest` dataclass 생성 (ticker, horizon, include_news, include_indicators)
  - `PredictionResult` dataclass 생성 (ticker, current_price, predicted_price, confidence, reasoning, chart_data)
  - `@property` 메서드: change_dollars, change_percent
  - Zero division 방지

  **Must NOT do**:
  - AI 모델 로직 포함 (service 레이어에서 처리)
  - 불필요한 validation (service에서)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 단순 데이터 클래스
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 1, 2와 병렬)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 9, 13-16
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:159-187` - domain/prediction.py 코드 예시

  **Acceptance Criteria**:
  - [ ] `PredictionRequest` dataclass 4개 필드
  - [ ] `PredictionResult` dataclass 6개 필드
  - [ ] `change_percent`에서 current_price == 0 처리

  **QA Scenarios**:
  ```
  Scenario: 예측 변화율 계산
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from domain.prediction import PredictionResult; r = PredictionResult('AAPL', 150, 160, 75, 'Test'); print(f'{r.change_percent:.2f}%')"
      2. 출력 확인: "6.67%"
    Expected Result: 정확한 퍼센트
    Evidence: .sisyphus/evidence/task-3-prediction-change.txt
  ```

  **Evidence to Capture**:
  - [ ] task-3-prediction-change.txt

  **Commit**: YES
  - Message: `feat(domain): add PredictionRequest, PredictionResult models`
  - Files: `domain/prediction.py`, `domain/__init__.py`

---

### Wave 2: Adapters (Phase 2)

- [x] 4. adapters/market_data.py 생성 (병렬 API 구현)

  **What to do**:
  - `MarketDataAdapter` 클래스 생성
  - `__init__(max_workers=10)` 생성자
  - `fetch_current_prices(tickers: List[str]) -> Dict[str, float]` - ThreadPoolExecutor 병렬 호출
  - `fetch_historical_data(ticker, period, interval) -> pd.DataFrame` - 단일 티커
  - `fetch_ticker_info(ticker) -> dict` - 섹터/산업 정보
  - 에러 핸들링: 개별 티커 실패 시 None 반환, 전체 중단 방지

  **Must NOT do**:
  - `yf.download()` 사용 금지 (Issue #2557) - `Ticker().history()` 사용
  - 불필요한 래퍼 함수 (yfinance 직접 호출로 충분한 경우)
  - 과도한 try/except (예상 가능한 에러만 처리)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: 병렬 처리 구현, 에러 핸들링 복잡도
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 5, 6과 병렬)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 7-9
  - **Blocked By**: Task 1-3

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:203-260` - adapters/market_data.py 코드 예시
  - `.sisyphus/drafts/portfolio-editor-refresh-loss.md:397-478` - 병렬 API 구현 패턴
  - yfinance Issue #2557: `Ticker().history()` 사용, `download()` 피하기

  **Acceptance Criteria**:
  - [ ] ThreadPoolExecutor 사용 확인: `grep -n "ThreadPoolExecutor" adapters/market_data.py`
  - [ ] `yf.download` 사용 안 함: `grep -n "yf.download" adapters/market_data.py` → 빈 결과
  - [ ] 5개 티커 조회 < 1초: 성능 테스트

  **QA Scenarios**:
  ```
  Scenario: 병렬 가격 조회 성능
    Tool: Bash
    Steps:
      1. cd /home/pcho/projects/AutoQuant
      2. python3 -c "import time; from adapters.market_data import MarketDataAdapter; adapter = MarketDataAdapter(max_workers=10); start = time.time(); prices = adapter.fetch_current_prices(['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']); elapsed = time.time() - start; print(f'Elapsed: {elapsed:.2f}s, Prices: {len(prices)}')"
      3. 확인: elapsed < 1.5초, len(prices) >= 4 (최소 4개 성공)
    Expected Result: 1.5초 이내, 4개 이상 티커 성공
    Evidence: .sisyphus/evidence/task-4-parallel-performance.txt

  Scenario: 개별 실패 처리
    Tool: Bash
    Steps:
      1. python3 -c "from adapters.market_data import MarketDataAdapter; adapter = MarketDataAdapter(); prices = adapter.fetch_current_prices(['AAPL', 'INVALID_TICKER_XYZ']); print(f'AAPL: {prices.get(\"AAPL\")}, INVALID: {prices.get(\"INVALID_TICKER_XYZ\")}')"
      2. 확인: AAPL 가격 존재, INVALID는 None 또는 키 없음
    Expected Result: 부분 실패 시 나머지 정상 처리
    Evidence: .sisyphus/evidence/task-4-error-handling.txt
  ```

  **Evidence to Capture**:
  - [ ] task-4-parallel-performance.txt
  - [ ] task-4-error-handling.txt

  **Commit**: YES
  - Message: `feat(adapters): add MarketDataAdapter with parallel API calls`
  - Files: `adapters/market_data.py`, `adapters/__init__.py`

---

- [x] 5. adapters/db_client.py 생성

  **What to do**:
  - `DBClient` 클래스 생성
  - `__init__(supabase_url, supabase_key)` - Supabase 클라이언트 생성
  - `fetch_positions(user_id) -> List[Position]` - holdings 테이블 조회
  - `save_positions(user_id, positions)` - 기존 삭제 후 재생성
  - `fetch_orders(user_id) -> List[Order]` - orders 테이블 조회
  - `save_order(user_id, order) -> bool` - 주문 저장

  **Must NOT do**:
  - Supabase 클라이언트를 매 호출마다 재생성 (생성자에서 한 번만)
  - 복잡한 ORM 래퍼 (간단한 CRUD만)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 단순 CRUD 래퍼
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 4, 6과 병렬)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 7-8
  - **Blocked By**: Task 2

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:262-320` - adapters/db_client.py 코드 예시
  - 기존 `portfolio.py:24-65` - Supabase 사용 패턴 참고

  **Acceptance Criteria**:
  - [ ] Supabase 클라이언트 생성 확인: `grep -n "create_client" adapters/db_client.py`
  - [ ] Domain model import 확인: `grep -n "from domain.position import" adapters/db_client.py`

  **QA Scenarios**:
  ```
  Scenario: DB 클라이언트 초기화
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from adapters.db_client import DBClient; client = DBClient('https://test.supabase.co', 'test-key'); print('Client created')"
      2. 에러 없이 "Client created" 출력
    Expected Result: 정상 초기화
    Evidence: .sisyphus/evidence/task-5-db-init.txt
  ```

  **Evidence to Capture**:
  - [ ] task-5-db-init.txt

  **Commit**: YES
  - Message: `feat(adapters): add DBClient for Supabase integration`
  - Files: `adapters/db_client.py`, `adapters/__init__.py`

---

- [x] 6. adapters/news_provider.py 생성 (스텁)

  **What to do**:
  - `NewsProvider` 클래스 생성
  - `__init__(api_key)` 생성자
  - `fetch_news(ticker, days=7) -> List[Dict]` - 빈 리스트 반환 (스텁)
  - `get_sentiment(article) -> float` - 0.0 반환 (스텁)
  - 주석: "Phase 5에서 실제 API 연동 예정"

  **Must NOT do**:
  - 실제 API 호출 (Phase 5에서)
  - 복잡한 스텁 로직

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 스텁만 생성
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 4, 5와 병렬)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 9, 13
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:322-334` - adapters/news_provider.py 스텁 예시

  **Acceptance Criteria**:
  - [ ] `NewsProvider` 클래스 존재
  - [ ] `fetch_news()` 빈 리스트 반환
  - [ ] `get_sentiment()` 0.0 반환

  **QA Scenarios**:
  ```
  Scenario: 스텁 동작 확인
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from adapters.news_provider import NewsProvider; provider = NewsProvider('test-key'); news = provider.fetch_news('AAPL'); print(f'News count: {len(news)}')"
      2. 출력: "News count: 0"
    Expected Result: 빈 리스트
    Evidence: .sisyphus/evidence/task-6-news-stub.txt
  ```

  **Evidence to Capture**:
  - [ ] task-6-news-stub.txt

  **Commit**: YES
  - Message: `feat(adapters): add NewsProvider stub for Phase 5`
  - Files: `adapters/news_provider.py`, `adapters/__init__.py`

---

### Wave 3: Services (Phase 3)

- [x] 7. services/portfolio_service.py 생성 (캐싱 포함)

  **What to do**:
  - `PortfolioService` 클래스 생성
  - `__init__(db: DBClient, market: MarketDataAdapter)` 생성자
  - `get_portfolio(user_id) -> Portfolio` - `@st.cache_data(ttl=300)` 적용
  - `update_positions(user_id, edited_df)` - DataFrame → Position 변환 후 저장
  - `label_risk(ticker: Ticker) -> RiskLevel` - 섹터 기반 위험도
  - `calculate_allocation(portfolio) -> Dict[str, float]` - 티커별 비중

  **Must NOT do**:
  - UI 코드 포함 (st.write, st.error 등 - 서비스는 순수 로직만)
  - 불필요한 중간 변수
  - 모든 함수에 캐싱 (get_portfolio만)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: 비즈니스 로직 핵심, 캐싱 전략 적용
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 8, 9와 병렬)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 10
  - **Blocked By**: Task 4, 5

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:357-422` - services/portfolio_service.py 코드 예시
  - `.sisyphus/drafts/portfolio-editor-refresh-loss.md:321-358` - 캐싱 전략
  - 기존 `portfolio.py:106-165` - 기존 로직 참고 (하지만 리팩토링 필요)

  **Acceptance Criteria**:
  - [ ] `@st.cache_data(ttl=300)` 데코레이터 확인: `grep -n "@st.cache_data" services/portfolio_service.py`
  - [ ] Domain model 사용 확인: `grep -n "Portfolio" services/portfolio_service.py`
  - [ ] `import streamlit` 없음 확인 (캐싱 import 제외): `grep -n "^import streamlit" services/portfolio_service.py` → 캐싱만

  **QA Scenarios**:
  ```
  Scenario: Portfolio 조회 (모킹)
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "
from domain.position import Position
from services.portfolio_service import PortfolioService

class MockDB:
    def fetch_positions(self, user_id):
        return [Position('AAPL', 10, 150, 0)]

class MockMarket:
    def fetch_current_prices(self, tickers):
        return {'AAPL': 160.0}

service = PortfolioService(MockDB(), MockMarket())
portfolio = service.get_portfolio('test')
print(f'Positions: {len(portfolio.positions)}, P/L: ${portfolio.positions[0].pnl_dollars}')
"
      2. 출력: "Positions: 1, P/L: $100.0"
    Expected Result: 정확한 계산
    Evidence: .sisyphus/evidence/task-7-portfolio-service.txt

  Scenario: Risk labeling
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "from domain.ticker import Ticker, Sector, RiskLevel; from services.portfolio_service import PortfolioService; service = PortfolioService(None, None); t = Ticker('AAPL', Sector.TECH, RiskLevel.MEDIUM); risk = service.label_risk(t); print(f'Risk: {risk.value}')"
      2. 출력: "Risk: high" (TECH는 high risk)
    Expected Result: TECH → HIGH
    Evidence: .sisyphus/evidence/task-7-risk-label.txt
  ```

  **Evidence to Capture**:
  - [ ] task-7-portfolio-service.txt
  - [ ] task-7-risk-label.txt

  **Commit**: YES
  - Message: `feat(services): add PortfolioService with caching`
  - Files: `services/portfolio_service.py`, `services/__init__.py`

---

- [x] 8. services/trading_service.py 생성

  **What to do**:
  - `TradingService` 클래스 생성
  - `__init__(db, market)` 생성자
  - `execute_order(user_id, order, cash_balance) -> Dict` - 주문 실행 및 검증
  - `calculate_pnl(positions) -> Dict` - 총 P/L, 티커별 P/L
  - 수수료 계산 (0.1%)
  - 매수/매도 검증 (잔고/수량 부족 시 FAILED 반환)

  **Must NOT do**:
  - UI 에러 메시지 (딕셔너리로 반환만)
  - 불필요한 validation 레이어

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: 주문 검증 로직, 에러 처리
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 7, 9와 병렬)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 11
  - **Blocked By**: Task 4, 5

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:424-486` - services/trading_service.py 코드 예시
  - 기존 `paper_trading.py:140-220` - 기존 주문 로직 참고

  **Acceptance Criteria**:
  - [ ] `execute_order()` 반환 타입 Dict 확인
  - [ ] 수수료 계산 0.1% 확인: `grep -n "0.001" services/trading_service.py`

  **QA Scenarios**:
  ```
  Scenario: 매수 주문 성공
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "
from domain.position import Order
from datetime import datetime
from services.trading_service import TradingService

class MockDB:
    def save_order(self, user_id, order): return True
    def fetch_positions(self, user_id): return []

order = Order('AAPL', 'BUY', 10, 150, datetime.now())
service = TradingService(MockDB(), None)
result = service.execute_order('test', order, 2000)
print(f'Status: {result[\"status\"]}, Remaining: ${result[\"remaining_cash\"]:.2f}')
"
      2. 출력: "Status: SUCCESS, Remaining: $498.50" (2000 - 1500 - 1.5 fee)
    Expected Result: 성공 및 정확한 잔고
    Evidence: .sisyphus/evidence/task-8-buy-success.txt

  Scenario: 매수 주문 실패 (잔고 부족)
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "
from domain.position import Order
from datetime import datetime
from services.trading_service import TradingService

class MockDB:
    def save_order(self, user_id, order): return True

order = Order('AAPL', 'BUY', 100, 150, datetime.now())
service = TradingService(MockDB(), None)
result = service.execute_order('test', order, 1000)
print(f'Status: {result[\"status\"]}, Reason: {result[\"reason\"]}')
"
      2. 출력: "Status: FAILED, Reason: Insufficient cash"
    Expected Result: 실패 및 이유
    Evidence: .sisyphus/evidence/task-8-buy-fail.txt
  ```

  **Evidence to Capture**:
  - [ ] task-8-buy-success.txt
  - [ ] task-8-buy-fail.txt

  **Commit**: YES
  - Message: `feat(services): add TradingService with order validation`
  - Files: `services/trading_service.py`, `services/__init__.py`

---

- [x] 9. services/prediction_service.py 생성 (스텁)

  **What to do**:
  - `PredictionService` 클래스 생성
  - `__init__(market, news)` 생성자
  - `predict_price(request) -> PredictionResult` - 임시: 현재가 +5% 반환
  - 주석: "Phase 5에서 실제 AI 로직 구현"

  **Must NOT do**:
  - 실제 AI 모델 (Phase 5에서)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 스텁만
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 7, 8과 병렬)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 12, 14-15
  - **Blocked By**: Task 4, 6

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:488-507` - services/prediction_service.py 스텁 예시

  **Acceptance Criteria**:
  - [ ] `predict_price()` 메서드 존재
  - [ ] `PredictionResult` 반환

  **QA Scenarios**:
  ```
  Scenario: 스텁 예측
    Tool: Bash (Python REPL)
    Steps:
      1. python3 -c "
from domain.prediction import PredictionRequest, PredictionResult
from services.prediction_service import PredictionService

class MockMarket:
    def fetch_current_prices(self, tickers):
        return {'AAPL': 150.0}

service = PredictionService(MockMarket(), None)
req = PredictionRequest('AAPL', '1 week')
result = service.predict_price(req)
print(f'Predicted: ${result.predicted_price:.2f}, Confidence: {result.confidence}%')
"
      2. 출력: "Predicted: $157.50, Confidence: 50.0%" (150 * 1.05)
    Expected Result: 스텁 예측값
    Evidence: .sisyphus/evidence/task-9-prediction-stub.txt
  ```

  **Evidence to Capture**:
  - [ ] task-9-prediction-stub.txt

  **Commit**: YES
  - Message: `feat(services): add PredictionService stub for Phase 5`
  - Files: `services/prediction_service.py`, `services/__init__.py`

---

### Wave 4: UI Layer (Phase 4)

- [x] 10. ui/portfolio_tab.py 생성 (조건부 refresh)

  **What to do**:
  - `render_portfolio_tab(portfolio_service)` 함수 생성
  - Portfolio 조회 및 테이블 렌더링 (`st.data_editor`)
  - 조건부 refresh 적용: 셀 편집 시 rerun 방지 (`on_change=None`)
  - 저장 버튼 클릭 시에만 `st.rerun()`
  - 수동 새로고침 버튼 (`st.cache_data.clear()`)
  - 할당 차트 (plotly pie chart)

  **Must NOT do**:
  - 비즈니스 로직 포함 (P/L 계산 등 - service에서)
  - 매 render마다 가격 조회 (캐싱된 service 호출만)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Reason**: Streamlit UI, 데이터 시각화
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 11, 12와 병렬)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 17-18
  - **Blocked By**: Task 7

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:527-616` - ui/portfolio_tab.py 코드 예시
  - `.sisyphus/drafts/portfolio-editor-refresh-loss.md:480-543` - 조건부 refresh 패턴
  - 기존 `portfolio.py:118-165` - 기존 UI 코드 참고 (하지만 조건부 refresh 추가)

  **Acceptance Criteria**:
  - [ ] `st.data_editor(..., on_change=None)` 확인: `grep -n "on_change=None" ui/portfolio_tab.py`
  - [ ] `st.button("💾 Save")` 후 `st.rerun()` 확인
  - [ ] `st.cache_data.clear()` 새로고침 버튼 확인

  **QA Scenarios**:
  ```
  Scenario: Portfolio 탭 렌더링 (Playwright)
    Tool: Playwright (dev-browser skill)
    Preconditions: streamlit run app.py 실행 중
    Steps:
      1. 브라우저 열기: http://localhost:8501
      2. "Portfolio" 탭 클릭
      3. 테이블 존재 확인: CSS selector "div[data-testid='stDataFrame']"
      4. "Save Changes" 버튼 존재 확인: button:has-text("💾 Save Changes")
      5. 스크린샷 캡처
    Expected Result: 테이블과 버튼 표시
    Failure Indicators: 테이블 없음, 버튼 없음
    Evidence: .sisyphus/evidence/task-10-portfolio-tab-render.png

  Scenario: Edit state loss 해결 (Playwright)
    Tool: Playwright
    Preconditions: 포트폴리오에 1개 이상 포지션 존재
    Steps:
      1. "Portfolio" 탭에서 첫 번째 Quantity 셀 클릭
      2. 값을 "999"로 변경
      3. 다른 셀 클릭 (Buy Price 셀)
      4. 다시 Quantity 셀 확인
      5. 값이 "999"로 유지되는지 확인
    Expected Result: 값 유지 (이전에는 원래 값으로 리셋됨)
    Failure Indicators: 값이 원래 값으로 돌아감
    Evidence: .sisyphus/evidence/task-10-edit-state-preserved.png
  ```

  **Evidence to Capture**:
  - [ ] task-10-portfolio-tab-render.png
  - [ ] task-10-edit-state-preserved.png

  **Commit**: YES
  - Message: `feat(ui): add portfolio_tab with conditional refresh`
  - Files: `ui/portfolio_tab.py`, `ui/__init__.py`

---

- [x] 11. ui/paper_trading_tab.py 생성

  **What to do**:
  - `render_trading_tab(trading_service)` 함수 생성
  - 주문 입력 폼 (ticker, action, quantity, price)
  - 주문 실행 버튼
  - 결과 표시 (성공/실패 메시지)
  - 잔고 표시 (`st.session_state.cash`)

  **Must NOT do**:
  - 주문 검증 로직 (service에서)
  - 복잡한 UI 상태 관리 (session_state는 cash만)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Reason**: Streamlit 폼 UI
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 10, 12와 병렬)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 17-18
  - **Blocked By**: Task 8

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:618-674` - ui/paper_trading_tab.py 코드 예시
  - 기존 `paper_trading.py:270-350` - 기존 UI 참고

  **Acceptance Criteria**:
  - [ ] `st.text_input("Ticker")` 확인
  - [ ] `st.radio("Action", ["BUY", "SELL"])` 확인
  - [ ] `st.button("Execute Order")` 확인

  **QA Scenarios**:
  ```
  Scenario: Trading 탭 렌더링 (Playwright)
    Tool: Playwright
    Steps:
      1. "Paper Trading" 탭 클릭
      2. Ticker 입력 필드 확인: input[aria-label="Ticker"]
      3. "Execute Order" 버튼 확인
      4. 스크린샷
    Expected Result: 폼 표시
    Evidence: .sisyphus/evidence/task-11-trading-tab-render.png

  Scenario: 주문 실행 (Playwright)
    Tool: Playwright
    Steps:
      1. Ticker 입력: "AAPL"
      2. Action 선택: "BUY"
      3. Quantity 입력: "10"
      4. Price 입력: "150"
      5. "Execute Order" 클릭
      6. 성공 메시지 확인: "✅ BUY 10 AAPL"
    Expected Result: 성공 메시지 표시
    Evidence: .sisyphus/evidence/task-11-order-execution.png
  ```

  **Evidence to Capture**:
  - [ ] task-11-trading-tab-render.png
  - [ ] task-11-order-execution.png

  **Commit**: YES
  - Message: `feat(ui): add paper_trading_tab`
  - Files: `ui/paper_trading_tab.py`, `ui/__init__.py`

---

- [x] 12. ui/prediction_tab.py 생성 (스텁)

  **What to do**:
  - `render_prediction_tab(prediction_service)` 함수 생성
  - 입력 폼 (ticker, horizon)
  - 예측 버튼
  - 결과 표시 (스텁 데이터)
  - "Phase 5에서 완성 예정" 안내 메시지

  **Must NOT do**:
  - 실제 AI 로직 (Phase 5에서)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Reason**: Streamlit UI
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 10, 11과 병렬)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 16
  - **Blocked By**: Task 9

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:676-714` - ui/prediction_tab.py 스텁 예시

  **Acceptance Criteria**:
  - [ ] `st.info()` 안내 메시지 확인
  - [ ] `st.button("🚀 Predict Price")` 확인

  **QA Scenarios**:
  ```
  Scenario: Prediction 탭 스텁 (Playwright)
    Tool: Playwright
    Steps:
      1. "AI Prediction" 탭 클릭
      2. 안내 메시지 확인: "This feature will be fully implemented in Phase 5"
      3. "🚀 Predict Price" 버튼 클릭
      4. 결과 표시 확인 (스텁 데이터)
    Expected Result: 스텁 UI 동작
    Evidence: .sisyphus/evidence/task-12-prediction-tab-stub.png
  ```

  **Evidence to Capture**:
  - [ ] task-12-prediction-tab-stub.png

  **Commit**: YES
  - Message: `feat(ui): add prediction_tab stub for Phase 5`
  - Files: `ui/prediction_tab.py`, `ui/__init__.py`

---

- [x] 12A. ui/settings_tab.py 생성 (캐시 삭제 기능)

  **What to do**:
  - `render_settings_tab()` 함수 생성
  - "Clear All Caches" 버튼 추가
  - 버튼 클릭 시 `st.cache_data.clear()` 호출
  - 성공 메시지 표시 (st.success)
  - 캐시된 항목 설명 추가 (포트폴리오 데이터, 가격 정보, AI 예측 결과 등)

  **Must NOT do**:
  - 다른 설정 항목 추가 (사용자가 명시한 것만: 캐시 삭제)
  - 복잡한 설정 UI (단순하게 버튼 하나만)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 간단한 UI 탭, 1개 버튼만
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 10, 11, 12와 병렬)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 17-18
  - **Blocked By**: None (독립적)

  **References**:
  - Streamlit caching docs: https://docs.streamlit.io/library/api-reference/performance/st.cache_data
  - `st.cache_data.clear()` API reference

  **Acceptance Criteria**:
  - [ ] `st.button("🗑️ Clear All Caches")` 존재 확인: `grep -n "Clear All Caches" ui/settings_tab.py`
  - [ ] `st.cache_data.clear()` 호출 확인: `grep -n "cache_data.clear()" ui/settings_tab.py`
  - [ ] `st.success()` 성공 메시지 확인

  **QA Scenarios**:
  ```
  Scenario: Settings 탭 렌더링 (Playwright)
    Tool: Playwright (dev-browser skill)
    Preconditions: streamlit run app.py 실행 중
    Steps:
      1. 브라우저 열기: http://localhost:8501
      2. "Settings" 탭 클릭
      3. "Clear All Caches" 버튼 존재 확인: button:has-text("🗑️ Clear All Caches")
      4. 캐시 설명 텍스트 확인
      5. 스크린샷 캡처
    Expected Result: 버튼과 설명 텍스트 표시
    Failure Indicators: 버튼 없음, 탭 렌더링 실패
    Evidence: .sisyphus/evidence/task-12a-settings-tab-render.png

  Scenario: 캐시 삭제 동작 확인 (Playwright)
    Tool: Playwright
    Preconditions: Portfolio 탭에서 데이터 로드하여 캐시 생성됨
    Steps:
      1. "Portfolio" 탭 방문하여 데이터 로드 (캐시 생성)
      2. "Settings" 탭 클릭
      3. "Clear All Caches" 버튼 클릭
      4. 성공 메시지 확인: "✅ All caches cleared successfully"
      5. "Portfolio" 탭 재방문
      6. 데이터 다시 로드되는지 확인 (캐시 미사용 = 약간의 로딩 시간)
    Expected Result: 성공 메시지 표시, 캐시 재생성됨
    Failure Indicators: 에러 메시지, 캐시 미삭제
    Evidence: .sisyphus/evidence/task-12a-cache-clear-success.png
  ```

  **Evidence to Capture**:
  - [ ] task-12a-settings-tab-render.png
  - [ ] task-12a-cache-clear-success.png

  **Commit**: YES
  - Message: `feat(ui): add settings_tab with cache clear functionality`
  - Files: `ui/settings_tab.py`, `ui/__init__.py`

---

### Wave 5: AI Prediction (Phase 5)

- [x] 13. adapters/news_provider.py 완성 (NewsAPI 통합)

  **What to do**:
  - `fetch_news()` 실제 구현 (NewsAPI 또는 Alpha Vantage)
  - `get_sentiment()` 구현 (키워드 기반 또는 FinBERT)
  - API key 관리 (`st.secrets` 사용)
  - 에러 핸들링 (API 실패 시 빈 리스트 반환)

  **Must NOT do**:
  - 복잡한 NLP 모델 (간단한 키워드 또는 외부 API)
  - API key 하드코딩

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: 외부 API 통합, 에러 처리
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Task 13 → 14-15)
  - **Blocks**: Task 14-15
  - **Blocked By**: Task 6

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:737-790` - adapters/news_provider.py 완성 예시
  - NewsAPI 문서: https://newsapi.org/docs/endpoints/everything

  **Acceptance Criteria**:
  - [ ] NewsAPI 호출 확인: `grep -n "newsapi.org" adapters/news_provider.py`
  - [ ] `get_sentiment()` 반환 값 -1 ~ 1 범위

  **QA Scenarios**:
  ```
  Scenario: 뉴스 조회 (실제 API)
    Tool: Bash
    Preconditions: NewsAPI key 설정 (.streamlit/secrets.toml)
    Steps:
      1. python3 -c "
import sys; sys.path.insert(0, '/home/pcho/projects/AutoQuant')
from adapters.news_provider import NewsProvider
import streamlit as st
provider = NewsProvider(st.secrets.get('newsapi', {}).get('key', 'DEMO_KEY'))
news = provider.fetch_news('AAPL', days=7)
print(f'News count: {len(news)}')
"
      2. 출력: "News count: N" (N >= 0)
    Expected Result: 뉴스 조회 성공
    Evidence: .sisyphus/evidence/task-13-news-fetch.txt

  Scenario: 감정 분석
    Tool: Bash
    Steps:
      1. python3 -c "
from adapters.news_provider import NewsProvider
provider = NewsProvider('test')
article = {'title': 'Apple stock surges on strong earnings', 'description': 'Profit beats expectations'}
sentiment = provider.get_sentiment(article)
print(f'Sentiment: {sentiment}')
assert -1 <= sentiment <= 1, 'Sentiment out of range'
"
      2. 출력: "Sentiment: 0.X" (positive 예상)
    Expected Result: -1 ~ 1 범위
    Evidence: .sisyphus/evidence/task-13-sentiment.txt
  ```

  **Evidence to Capture**:
  - [ ] task-13-news-fetch.txt
  - [ ] task-13-sentiment.txt

  **Commit**: YES
  - Message: `feat(adapters): implement NewsProvider with NewsAPI integration`
  - Files: `adapters/news_provider.py`

---

- [x] 14. services/prediction_service.py - 기술적 지표 추가

  **What to do**:
  - `calculate_indicators(ticker) -> Dict` 메서드 추가
  - RSI, MACD, Bollinger Bands, SMA(50, 200) 계산
  - `pandas_ta` 또는 `ta-lib` 사용
  - `generate_signals(indicators) -> Dict` 메서드 추가
  - 지표 기반 매매 신호 (OVERBOUGHT, OVERSOLD, BULLISH, BEARISH 등)

  **Must NOT do**:
  - 과도한 지표 (5-6개면 충분)
  - 복잡한 백테스팅 로직

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: 금융 지표 계산 로직
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 15와 병렬 가능하지만 Task 14 먼저 권장)
  - **Parallel Group**: Wave 5
  - **Blocks**: Task 15-16
  - **Blocked By**: Task 9, 13

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:792-883` - 기술적 지표 계산 예시
  - pandas_ta 문서: https://github.com/twopirllc/pandas-ta

  **Acceptance Criteria**:
  - [ ] `calculate_indicators()` 메서드 존재
  - [ ] 반환 dict에 'rsi', 'macd', 'bb_upper', 'sma_50' 키 포함
  - [ ] `generate_signals()` 메서드 존재

  **QA Scenarios**:
  ```
  Scenario: 기술적 지표 계산
    Tool: Bash
    Steps:
      1. python3 -c "
from services.prediction_service import PredictionService
from adapters.market_data import MarketDataAdapter

service = PredictionService(MarketDataAdapter(), None)
indicators = service.calculate_indicators('AAPL')
print(f'RSI: {indicators.get(\"rsi\")}, MACD: {indicators.get(\"macd\")}')
assert 'rsi' in indicators
assert 'macd' in indicators
"
      2. 출력: RSI, MACD 값 존재
    Expected Result: 지표 계산 성공
    Evidence: .sisyphus/evidence/task-14-indicators.txt

  Scenario: 매매 신호 생성
    Tool: Bash
    Steps:
      1. python3 -c "
from services.prediction_service import PredictionService

service = PredictionService(None, None)
indicators = {'rsi': 75, 'macd': 1.5, 'macd_signal': 1.0, 'current_price': 150, 'bb_upper': 155, 'bb_lower': 145, 'sma_50': 148, 'sma_200': 140}
signals = service.generate_signals(indicators)
print(f'RSI signal: {signals.get(\"rsi\")}, MACD signal: {signals.get(\"macd\")}')
"
      2. 출력: "RSI signal: OVERBOUGHT, MACD signal: BULLISH"
    Expected Result: 정확한 신호
    Evidence: .sisyphus/evidence/task-14-signals.txt
  ```

  **Evidence to Capture**:
  - [ ] task-14-indicators.txt
  - [ ] task-14-signals.txt

  **Commit**: YES
  - Message: `feat(services): add technical indicators to PredictionService`
  - Files: `services/prediction_service.py`

---

- [x] 15. services/prediction_service.py - AI 모델 (규칙 기반)

  **What to do**:
  - `predict_price()` 메서드 완성
  - 뉴스 감정 분석 (30% 가중치)
  - 기술적 지표 신호 (70% 가중치: RSI 20%, MACD 30%, MA 20%)
  - 점수 계산 (-1 ~ 1 범위)
  - 가격 예측 (현재가 × (1 + score × max_change))
  - 신뢰도 계산 (abs(score) × 100, 최대 85%)
  - 근거 생성 (뉴스 감정 + 지표 신호 요약)

  **Must NOT do**:
  - 복잡한 ML 모델 (규칙 기반으로 충분)
  - 과적합 방지 불필요 (간단한 로직)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Reason**: 가중치 조합 로직, 신뢰도 계산
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (Task 14 필요)
  - **Parallel Group**: Sequential
  - **Blocks**: Task 16
  - **Blocked By**: Task 14

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:887-960` - 규칙 기반 AI 모델 예시

  **Acceptance Criteria**:
  - [ ] `predict_price()` 실제 예측 로직 구현
  - [ ] 반환값에 `reasoning` 필드 포함
  - [ ] 신뢰도 0-100 범위

  **QA Scenarios**:
  ```
  Scenario: AI 가격 예측 (통합)
    Tool: Bash
    Steps:
      1. python3 -c "
from domain.prediction import PredictionRequest
from services.prediction_service import PredictionService
from adapters.market_data import MarketDataAdapter
from adapters.news_provider import NewsProvider
import streamlit as st

market = MarketDataAdapter()
news = NewsProvider(st.secrets.get('newsapi', {}).get('key', 'DEMO'))
service = PredictionService(market, news)

req = PredictionRequest('AAPL', '1 week', include_news=True, include_indicators=True)
result = service.predict_price(req)

print(f'Current: ${result.current_price:.2f}')
print(f'Predicted: ${result.predicted_price:.2f}')
print(f'Confidence: {result.confidence}%')
print(f'Reasoning: {result.reasoning[:100]}...')

assert 0 <= result.confidence <= 100
"
      2. 출력: 예측 결과 및 근거
    Expected Result: 유효한 예측값
    Evidence: .sisyphus/evidence/task-15-ai-prediction.txt
  ```

  **Evidence to Capture**:
  - [ ] task-15-ai-prediction.txt

  **Commit**: YES
  - Message: `feat(services): implement rule-based AI price prediction`
  - Files: `services/prediction_service.py`

---

- [x] 16. ui/prediction_tab.py 완성

  **What to do**:
  - 스텁 제거, 실제 UI 구현
  - 예측 결과 표시 (현재가, 예측가, 변화율, 신뢰도)
  - 근거 표시 (뉴스 감정 + 지표 신호)
  - 예측 히스토리 저장 (`st.session_state`)
  - 히스토리 테이블 표시

  **Must NOT do**:
  - 복잡한 차트 (간단한 metric만)
  - 과도한 UI 꾸미기

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Reason**: Streamlit UI, 결과 시각화
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 20
  - **Blocked By**: Task 12, 15

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:1052-1115` - ui/prediction_tab.py 완성 예시

  **Acceptance Criteria**:
  - [ ] `st.metric()` 3개 (현재가, 예측가, 신뢰도)
  - [ ] 근거 표시: `st.markdown(result.reasoning)`
  - [ ] 히스토리 저장: `st.session_state.prediction_history`

  **QA Scenarios**:
  ```
  Scenario: AI 예측 UI (Playwright)
    Tool: Playwright
    Steps:
      1. "AI Prediction" 탭 클릭
      2. Ticker 입력: "AAPL"
      3. Horizon 선택: "1 week"
      4. "🚀 Predict Price" 클릭
      5. 결과 확인: "Current Price", "Predicted Price", "Confidence" 메트릭 존재
      6. 근거 확인: "Analysis" 섹션 존재
      7. 스크린샷
    Expected Result: 예측 결과 표시
    Evidence: .sisyphus/evidence/task-16-prediction-ui.png
  ```

  **Evidence to Capture**:
  - [ ] task-16-prediction-ui.png

  **Commit**: YES
  - Message: `feat(ui): complete prediction_tab with AI results display`
  - Files: `ui/prediction_tab.py`

---

### Wave 6: Cleanup & Testing (Phase 6)

- [x] 17. Legacy 코드 이동

  **What to do**:
  - `legacy/` 디렉토리 생성
  - `portfolio.py`, `chart.py`, `paper_trading.py`를 `legacy/`로 이동
  - Git으로 이동 (`git mv`)

  **Must NOT do**:
  - Legacy 코드 삭제 (참고용 보관)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 단순 파일 이동
  - **Skills**: [`git-master`]
  - **git-master**: Git 작업에 특화된 스킬

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 18과 병렬)
  - **Parallel Group**: Wave 6
  - **Blocks**: Task 19-20
  - **Blocked By**: Task 10-12

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:1138-1144` - Legacy 이동 예시

  **Acceptance Criteria**:
  - [ ] `legacy/` 디렉토리 존재
  - [ ] `legacy/portfolio.py`, `legacy/chart.py`, `legacy/paper_trading.py` 존재
  - [ ] 원래 위치에 파일 없음

  **QA Scenarios**:
  ```
  Scenario: Legacy 파일 이동 확인
    Tool: Bash
    Steps:
      1. ls legacy/
      2. 출력 확인: portfolio.py, chart.py, paper_trading.py 존재
      3. ls *.py | grep -E "(portfolio|chart|paper_trading)"
      4. 출력: 빈 결과 (원래 위치에 없음)
    Expected Result: Legacy 폴더로 이동 완료
    Evidence: .sisyphus/evidence/task-17-legacy-moved.txt
  ```

  **Evidence to Capture**:
  - [ ] task-17-legacy-moved.txt

  **Commit**: YES
  - Message: `refactor: move legacy code to legacy/ folder`
  - Files: `legacy/portfolio.py`, `legacy/chart.py`, `legacy/paper_trading.py`

---

- [x] 18. app.py 업데이트 (의존성 주입 + Settings 탭)

  **What to do**:
  - `app.py` 완전히 재작성
  - 의존성 주입: `@st.cache_resource`로 서비스 싱글톤 생성
  - **4개 탭 렌더링** (`ui/` 모듈 import): Portfolio, Paper Trading, AI Prediction, **Settings**
  - Legacy import 제거

  **Must NOT do**:
  - 비즈니스 로직 포함 (UI 라우팅만)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: 의존성 주입 패턴 적용
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 17과 병렬)
  - **Parallel Group**: Wave 6
  - **Blocks**: Task 19-20
  - **Blocked By**: Task 10-12A (Settings 탭 포함)

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:1148-1200` - app.py 최종 버전
  - `ui/settings_tab.py` - Settings 탭 import 필요

  **Acceptance Criteria**:
  - [ ] `@st.cache_resource` 데코레이터 확인
  - [ ] `from ui.portfolio_tab import render_portfolio_tab` 확인
  - [ ] `from ui.settings_tab import render_settings_tab` 확인
  - [ ] Legacy import 없음: `grep -n "from portfolio import\|from chart import" app.py` → 빈 결과

  **QA Scenarios**:
  ```
  Scenario: 앱 실행 및 탭 전환 (Playwright)
    Tool: Playwright
    Preconditions: streamlit run app.py
    Steps:
      1. http://localhost:8501 열기
      2. **4개 탭** 존재 확인: "Portfolio", "Paper Trading", "AI Prediction", "Settings"
      3. 각 탭 클릭 후 에러 없이 렌더링 확인
      4. 스크린샷 각각
    Expected Result: 4개 탭 모두 정상 동작
    Evidence: .sisyphus/evidence/task-18-app-tabs.png

  Scenario: Settings 탭 통합 확인 (Playwright)
    Tool: Playwright
    Steps:
      1. "Settings" 탭 클릭
      2. "Clear All Caches" 버튼 존재 확인
      3. 버튼 클릭하여 동작 확인
    Expected Result: Settings 탭 정상 작동
    Evidence: .sisyphus/evidence/task-18-settings-integrated.png
  ```

  **Evidence to Capture**:
  - [ ] task-18-app-tabs.png
  - [ ] task-18-settings-integrated.png

  **Commit**: YES
  - Message: `refactor: update app.py with dependency injection and 4 tabs`
  - Files: `app.py`

---

- [x] 19. pytest 설정 및 테스트 작성

  **What to do**:
  - `tests/` 디렉토리 생성
  - `pytest.ini` 또는 `pyproject.toml` 설정
  - `tests/test_portfolio_service.py` 작성 (최소 3개 테스트)
  - `tests/test_trading_service.py` 작성 (최소 3개 테스트)
  - `tests/test_market_data.py` 작성 (최소 2개 테스트)
  - Mock 객체 사용 (DBClient, MarketDataAdapter)

  **Must NOT do**:
  - UI 테스트 (Playwright는 QA scenarios로 충분)
  - 과도한 테스트 (핵심 로직만)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: 테스트 작성, Mock 패턴
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 20과 병렬)
  - **Parallel Group**: Wave 6
  - **Blocks**: None
  - **Blocked By**: Task 17-18

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:1202-1294` - pytest 테스트 예시

  **Acceptance Criteria**:
  - [ ] `pytest` 실행 시 최소 8개 테스트 통과
  - [ ] `tests/test_portfolio_service.py` 존재
  - [ ] `tests/test_trading_service.py` 존재
  - [ ] `tests/test_market_data.py` 존재

  **QA Scenarios**:
  ```
  Scenario: pytest 실행
    Tool: Bash
    Steps:
      1. cd /home/pcho/projects/AutoQuant
      2. pytest -v
      3. 출력 확인: "X passed" (X >= 8)
    Expected Result: 모든 테스트 통과
    Evidence: .sisyphus/evidence/task-19-pytest-results.txt
  ```

  **Evidence to Capture**:
  - [ ] task-19-pytest-results.txt

  **Commit**: YES
  - Message: `test: add service layer unit tests`
  - Files: `tests/`, `pytest.ini`

---

- [x] 20. 통합 테스트 및 문서화

  **What to do**:
  - 수동 통합 테스트 체크리스트 실행
  - README.md 업데이트 (새 구조 설명)
  - 성능 측정 (5개 티커 조회 시간)
  - 최종 검증

  **Must NOT do**:
  - 과도한 문서화 (간단한 README 업데이트만)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: 통합 검증, 문서 작성
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 17-19

  **References**:
  - `.sisyphus/drafts/phase-1-6-guide.md:1296-1310` - 통합 테스트 체크리스트

  **Acceptance Criteria**:
  - [ ] Portfolio 편집 → 저장 → 새로고침 시 값 유지
  - [ ] 5개 티커 가격 조회 < 1초
  - [ ] AI Prediction 예측 결과 표시
  - [ ] README.md 업데이트 완료

  **QA Scenarios**:
  ```
  Scenario: 전체 기능 통합 테스트 (Playwright)
    Tool: Playwright
    Steps:
      1. Portfolio 탭에서 포지션 편집 → 저장 → 값 유지 확인
      2. Paper Trading 탭에서 주문 실행 → 성공 메시지 확인
      3. AI Prediction 탭에서 예측 실행 → 결과 표시 확인
      4. 각 단계 스크린샷
    Expected Result: 모든 기능 정상 동작
    Evidence: .sisyphus/evidence/task-20-integration-test.png

  Scenario: 성능 측정
    Tool: Bash
    Steps:
      1. python3 -c "
import time
from adapters.market_data import MarketDataAdapter

adapter = MarketDataAdapter(max_workers=10)
start = time.time()
prices = adapter.fetch_current_prices(['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'])
elapsed = time.time() - start

print(f'Elapsed: {elapsed:.2f}s')
assert elapsed < 1.0, f'Too slow: {elapsed}s'
"
      2. 출력: "Elapsed: 0.Xs"
    Expected Result: < 1초
    Evidence: .sisyphus/evidence/task-20-performance.txt
  ```

  **Evidence to Capture**:
  - [ ] task-20-integration-test.png
  - [ ] task-20-performance.txt

  **Commit**: YES
  - Message: `docs: update README with new architecture`
  - Files: `README.md`

---

## Commit Strategy

- **Wave 1**: 3개 커밋 (각 domain 모델)
- **Wave 2**: 3개 커밋 (각 adapter)
- **Wave 3**: 3개 커밋 (각 service)
- **Wave 4**: 3개 커밋 (각 UI 탭)
- **Wave 5**: 4개 커밋 (뉴스 API, 지표, AI 모델, UI 완성)
- **Wave 6**: 4개 커밋 (Legacy 이동, app.py, 테스트, 문서)

**총 커밋 수: 20개**

---

## Success Criteria

### Verification Commands
```bash
# 구조 검증
ls -la domain/ adapters/ services/ ui/ tests/ legacy/

# Streamlit 의존성 검증 (domain, services, adapters에 없어야 함)
grep -r "^import streamlit" domain/ services/ adapters/  # 빈 결과 (또는 캐싱만)

# 테스트 실행
pytest -v  # 최소 8개 통과

# 앱 실행
streamlit run app.py  # 에러 없이 실행

# 성능 측정
python3 -c "import time; from adapters.market_data import MarketDataAdapter; start = time.time(); MarketDataAdapter().fetch_current_prices(['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']); print(f'{time.time() - start:.2f}s')"  # < 1초
```

### Final Checklist
- [ ] All "Must Have" present
  - [ ] Edit state loss 해결
  - [ ] 병렬 API 호출 구현
  - [ ] 캐싱 적용
  - [ ] AI 가격 예측 기능
  - [ ] Anti-bloat 규칙 준수
- [ ] All "Must NOT Have" absent
  - [ ] FastAPI 전환 없음
  - [ ] 과도한 추상화 없음
  - [ ] 불필요한 중간 변수 없음
  - [ ] 명백한 주석 없음
- [ ] All tests pass
  - [ ] pytest 8개 이상 통과
  - [ ] 모든 QA scenarios 증거 파일 존재
- [ ] Performance targets met
  - [ ] 5개 티커 조회 < 1초
  - [ ] Portfolio 조회 캐시 적중 시 < 0.1초
