# Fix Missing streamlit-searchbox Dependency

## TL;DR

> **Quick Summary**: App crashes on startup with `ModuleNotFoundError: No module named 'streamlit_searchbox'` because `streamlit-searchbox` package is missing from both the virtual environment and `requirements.txt`. Fix by installing the package and updating the dependency file.
> 
> **Deliverables**:
> - `streamlit-searchbox==0.1.24` installed in `env/` virtual environment
> - `requirements.txt` updated with the missing dependency (version-pinned)
> - App starts and runs without import errors
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 (install) → Task 3 (verify) → Task 4 (commit)

---

## Context

### Original Request
User reported the AutoQuant Streamlit app won't start. Diagnosis revealed `paper_trading.py` line 8 imports `streamlit_searchbox` which is not installed.

### Interview Summary
**Key Discussions**:
- Confirmed `ModuleNotFoundError` via `python -c "from streamlit_searchbox import st_searchbox"`
- Package not in `requirements.txt` and not installed in `env/`
- User chose to install the package (not replace with basic Streamlit widgets)

**Research Findings**:
- `pip install --dry-run` confirms `streamlit-searchbox==0.1.24` installs cleanly with zero conflicts
- All transitive dependencies already satisfied by existing venv
- The `st_searchbox()` usage in `paper_trading.py:294` is correct API for this package version
- `requirements.txt` convention: all packages version-pinned with `==` (except `supabase` on line 52)

### Metis Review
**Identified Gaps** (addressed):
- Version pinning: Resolved — pin to `==0.1.24` matching project convention
- Alphabetical ordering: Resolved — insert after `streamlit==1.45.1`, before `ta==0.11.0`
- Supabase unpinned: Flagged but OUT OF SCOPE for this fix
- Post-fix verification: Must use `streamlit run` not bare Python import (Streamlit context dependency)

---

## Work Objectives

### Core Objective
Install the missing `streamlit-searchbox` package and add it to `requirements.txt` so the AutoQuant app starts without errors.

### Concrete Deliverables
- `streamlit-searchbox==0.1.24` installed in `env/` virtual environment
- `requirements.txt` line 42: `streamlit-searchbox==0.1.24`

### Definition of Done
- [ ] `env/bin/python -c "from streamlit_searchbox import st_searchbox; print('OK')"` → prints `OK`
- [ ] `env/bin/python -m pip check` → "No broken requirements found."
- [ ] `grep -F 'streamlit-searchbox==0.1.24' requirements.txt` → match found
- [ ] App starts: `streamlit run app.py --server.headless true` → "You can now view your Streamlit app"

### Must Have
- Package `streamlit-searchbox==0.1.24` installed in project venv
- `requirements.txt` updated with version-pinned entry in alphabetical order

### Must NOT Have (Guardrails)
- MUST NOT modify any Python source files (`.py`) — the code is correct as-is
- MUST NOT upgrade/downgrade any existing packages
- MUST NOT install any additional packages beyond `streamlit-searchbox`
- MUST NOT touch `.streamlit/secrets.toml` or any configuration files
- MUST NOT fix the unpinned `supabase` entry (out of scope)
- MUST NOT add a `pyproject.toml` or modernize dependency management
- MUST NOT add tests or test infrastructure
- MUST NOT update `run_instruction.txt`

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: None
- **Framework**: none

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI/Backend**: Use Bash — Run commands, assert output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — independent operations):
├── Task 1: Install streamlit-searchbox in venv [quick]
└── Task 2: Add streamlit-searchbox to requirements.txt [quick]

Wave 2 (After Wave 1 — verification):
└── Task 3: Verify & QA — all acceptance criteria [quick]

Wave 3 (After Wave 2 — commit):
└── Task 4: Commit the fix [quick]

Wave FINAL (After ALL tasks — independent review):
├── Task F1: Plan compliance audit (oracle)
└── Task F2: Scope fidelity check (deep)

Critical Path: Task 1 → Task 3 → Task 4
Parallel Speedup: Tasks 1 & 2 run simultaneously
Max Concurrent: 2 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 3 | 1 |
| 2 | — | 3 | 1 |
| 3 | 1, 2 | 4 | 2 |
| 4 | 3 | F1, F2 | 3 |
| F1 | 4 | — | FINAL |
| F2 | 4 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: **2 tasks** — T1 → `quick`, T2 → `quick`
- **Wave 2**: **1 task** — T3 → `quick`
- **Wave 3**: **1 task** — T4 → `quick` + `git-master`
- **FINAL**: **2 tasks** — F1 → `oracle`, F2 → `deep`

---

## TODOs

- [x] 1. Install streamlit-searchbox in venv

  **What to do**:
  - Run `env/bin/python -m pip install streamlit-searchbox==0.1.24` in `/home/pcho/projects/AutoQuant`
  - Verify installation with import test

  **Must NOT do**:
  - Install any other packages
  - Upgrade/downgrade existing packages
  - Modify any files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single shell command, trivial complexity
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: No git operations in this task
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `requirements.txt:41` — Shows `streamlit==1.45.1`, confirming Streamlit is installed. The searchbox package depends on streamlit>=1.0 which is satisfied.

  **API/Type References**:
  - `paper_trading.py:8` — `from streamlit_searchbox import st_searchbox` — This is the import that currently fails
  - `paper_trading.py:294-301` — `st_searchbox()` usage with parameters: `search_function`, `placeholder`, `label`, `key`, `clear_on_submit`, `default`

  **External References**:
  - PyPI: `https://pypi.org/project/streamlit-searchbox/` — Package source

  **WHY Each Reference Matters**:
  - `requirements.txt:41`: Confirms streamlit version compatibility — searchbox 0.1.24 requires streamlit>=1.0
  - `paper_trading.py:8,294`: Shows the exact import and API usage to verify compatibility with installed version

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Package installs successfully
    Tool: Bash
    Preconditions: Virtual environment exists at env/
    Steps:
      1. Run: env/bin/python -m pip install streamlit-searchbox==0.1.24
      2. Assert: exit code is 0
      3. Run: env/bin/python -c "from streamlit_searchbox import st_searchbox; print('OK')"
      4. Assert: stdout contains "OK"
    Expected Result: Package installed, import succeeds
    Failure Indicators: Non-zero exit code, "ERROR" in pip output, ImportError on verification
    Evidence: .sisyphus/evidence/task-1-install-success.txt

  Scenario: No dependency conflicts introduced
    Tool: Bash
    Preconditions: Package installed from previous scenario
    Steps:
      1. Run: env/bin/python -m pip check
      2. Assert: stdout contains "No broken requirements found."
    Expected Result: Zero broken requirements
    Failure Indicators: "has requirement" error messages
    Evidence: .sisyphus/evidence/task-1-no-conflicts.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-install-success.txt — pip install output + import verification
  - [ ] task-1-no-conflicts.txt — pip check output

  **Commit**: NO (groups with Task 4)

- [x] 2. Add streamlit-searchbox to requirements.txt

  **What to do**:
  - Edit `requirements.txt` to insert the line `streamlit-searchbox==0.1.24` after line 41 (`streamlit==1.45.1`) and before the current line 42 (`ta==0.11.0`)
  - Maintain alphabetical ordering

  **Must NOT do**:
  - Modify any other lines in `requirements.txt`
  - Change version numbers of existing packages
  - Modify any `.py` files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-line insertion in a text file
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: No git operations in this task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `requirements.txt:41` — `streamlit==1.45.1` — Insert AFTER this line
  - `requirements.txt:42` — `ta==0.11.0` — Insert BEFORE this line (it will shift to line 43)

  **WHY Each Reference Matters**:
  - Line 41-42: Exact insertion point to maintain alphabetical order (`streamlit` < `streamlit-searchbox` < `ta`)
  - Version pinning convention (`==`) matches all other entries in the file

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Line inserted in correct position
    Tool: Bash
    Preconditions: requirements.txt exists with streamlit==1.45.1 on line 41
    Steps:
      1. Run: grep -n 'streamlit' requirements.txt
      2. Assert: output shows streamlit==1.45.1 on line 41 and streamlit-searchbox==0.1.24 on line 42
      3. Run: sed -n '41,43p' requirements.txt
      4. Assert: line 41 is "streamlit==1.45.1", line 42 is "streamlit-searchbox==0.1.24", line 43 is "ta==0.11.0"
    Expected Result: New entry correctly positioned between streamlit and ta
    Failure Indicators: Wrong line number, wrong version, missing entry
    Evidence: .sisyphus/evidence/task-2-insertion-check.txt

  Scenario: No other lines modified
    Tool: Bash
    Preconditions: Edit completed
    Steps:
      1. Run: wc -l requirements.txt
      2. Assert: line count is 53 (was 52, added 1)
      3. Run: git diff requirements.txt
      4. Assert: diff shows exactly 1 line added, 0 lines removed, 0 lines modified
    Expected Result: Only one line added, nothing else changed
    Failure Indicators: More than 1 line changed, unexpected modifications
    Evidence: .sisyphus/evidence/task-2-no-side-effects.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-insertion-check.txt — grep output showing correct line position
  - [ ] task-2-no-side-effects.txt — diff showing only 1 line added

  **Commit**: NO (groups with Task 4)

- [x] 3. Verify & QA — all acceptance criteria

  **What to do**:
  - Run all verification commands sequentially
  - Verify package import, dependency health, requirements.txt, and app startup
  - Kill any leftover Streamlit processes after testing

  **Must NOT do**:
  - Modify any files
  - Install additional packages

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Running verification commands only
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1, Task 2

  **References**:

  **Pattern References**:
  - `paper_trading.py:8` — The import that was failing — verify it now succeeds
  - `app.py:4` — `from paper_trading import PaperTradingManager` — This was the crash path

  **WHY Each Reference Matters**:
  - These are the exact lines that caused the crash — verification must confirm they now work

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full verification suite
    Tool: Bash
    Preconditions: Tasks 1 and 2 completed
    Steps:
      1. Run: env/bin/python -c "from streamlit_searchbox import st_searchbox; print('OK')"
      2. Assert: stdout is "OK"
      3. Run: env/bin/python -m pip check
      4. Assert: stdout contains "No broken requirements found."
      5. Run: grep -F 'streamlit-searchbox==0.1.24' requirements.txt
      6. Assert: match found (exit code 0)
      7. Run: timeout 15 env/bin/python -m streamlit run app.py --server.headless true --server.port 8599 2>&1
      8. Assert: output contains "You can now view your Streamlit app"
      9. Kill any Streamlit process on port 8599
    Expected Result: All 4 checks pass
    Failure Indicators: Any check fails, ModuleNotFoundError, app crash
    Evidence: .sisyphus/evidence/task-3-full-verification.txt

  Scenario: No existing Streamlit processes interfered with
    Tool: Bash
    Preconditions: After test Streamlit was killed
    Steps:
      1. Run: lsof -i :8599 || true
      2. Assert: No process listening on port 8599
    Expected Result: Clean port state after test
    Failure Indicators: Orphaned Streamlit process
    Evidence: .sisyphus/evidence/task-3-clean-port.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-full-verification.txt — All verification outputs
  - [ ] task-3-clean-port.txt — Port cleanup confirmation

  **Commit**: NO (groups with Task 4)

- [x] 4. Commit the fix

  **What to do**:
  - Stage only `requirements.txt`
  - Commit with message: `fix: add missing streamlit-searchbox dependency to requirements.txt`
  - Verify commit is clean

  **Must NOT do**:
  - Stage any files other than `requirements.txt`
  - Modify commit history
  - Push to remote

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple git add + commit
  - **Skills**: [`git-master`]
    - `git-master`: Required for any git operations per skill policy

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: F1, F2
  - **Blocked By**: Task 3

  **References**:

  **Pattern References**:
  - `requirements.txt` — The only file that should be staged

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Clean commit with correct message
    Tool: Bash
    Preconditions: All verification passed (Task 3)
    Steps:
      1. Run: git add requirements.txt
      2. Run: git commit -m "fix: add missing streamlit-searchbox dependency to requirements.txt"
      3. Assert: exit code is 0
      4. Run: git log -1 --oneline
      5. Assert: output contains "fix: add missing streamlit-searchbox dependency"
      6. Run: git diff HEAD~1 --name-only
      7. Assert: output is exactly "requirements.txt" (no other files)
      8. Run: git status
      9. Assert: working tree is clean
    Expected Result: Single-file commit with correct message
    Failure Indicators: Multiple files in commit, wrong message, dirty working tree
    Evidence: .sisyphus/evidence/task-4-commit-verified.txt

  Scenario: Only requirements.txt was changed in commit
    Tool: Bash
    Preconditions: Commit completed
    Steps:
      1. Run: git diff HEAD~1 --stat
      2. Assert: shows "1 file changed, 1 insertion(+)"
      3. Run: git diff HEAD~1 -- requirements.txt
      4. Assert: shows only the added line "streamlit-searchbox==0.1.24"
    Expected Result: Minimal diff — exactly 1 line added
    Failure Indicators: More than 1 line changed, unexpected file modifications
    Evidence: .sisyphus/evidence/task-4-minimal-diff.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-commit-verified.txt — git log and status output
  - [ ] task-4-minimal-diff.txt — git diff stat and content

  **Commit**: YES
  - Message: `fix: add missing streamlit-searchbox dependency to requirements.txt`
  - Files: `requirements.txt`
  - Pre-commit: All QA scenarios from Task 3 passed

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 2 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (run `env/bin/python -c "from streamlit_searchbox import st_searchbox; print('OK')"` and `grep -F 'streamlit-searchbox==0.1.24' requirements.txt`). For each "Must NOT Have": verify no `.py` files were modified (`git diff HEAD~1 --name-only` should show only `requirements.txt`). Check evidence files exist in `.sisyphus/evidence/`.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (`git diff HEAD~1`). Verify 1:1 — only `requirements.txt` was changed and only one line was added (`streamlit-searchbox==0.1.24`). Check no other files were modified. Detect scope creep: any changes beyond the two deliverables.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Single atomic commit** after all verification passes
- Message: `fix: add missing streamlit-searchbox dependency to requirements.txt`
- Files: `requirements.txt` only
- Pre-commit check: All QA scenarios pass

---

## Success Criteria

### Verification Commands
```bash
env/bin/python -c "from streamlit_searchbox import st_searchbox; print('OK')"  # Expected: OK
env/bin/python -m pip check  # Expected: No broken requirements found.
grep -F 'streamlit-searchbox==0.1.24' requirements.txt  # Expected: streamlit-searchbox==0.1.24
timeout 15 env/bin/python -m streamlit run app.py --server.headless true --server.port 8599 2>&1 | grep 'You can now view'  # Expected: "You can now view your Streamlit app"
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] App starts without ModuleNotFoundError
