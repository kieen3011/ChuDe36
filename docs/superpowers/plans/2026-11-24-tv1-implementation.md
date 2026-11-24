# TV1 Implementation Plan

> **Execution:** Native implementation in this session, explicitly requested by the Master Prompt.

**Goal:** Deliver contract-compliant TV1 sensor architecture, manager, orchestrator, tests, and handoff documentation without implementing TV2–TV5.

**Architecture:** Domain model in `sensor.py`, ordered registry in `monitoring_manager.py`, deterministic orchestration in `main.py`, TV1-owned runtime defaults in `config.py`. External modules are injected and represented by test doubles in tests.

**Tech Stack:** Python 3 standard library, `unittest`, Git.

### Task 1: Sensor and subclasses

**Files:** Create `sensor.py`; test `tests/test_sensor.py`.

**Produces:** `Sensor(sensor_id, location_id, status="ACTIVE")`, `set_status`, `update_measurement`, `get_reading`, plus three thin subclasses with contract `TYPE_NAME` values.

- [x] Write failing tests for construction, seven-field schema, inheritance, status transitions, accepted measurement, rejected non-ACTIVE update, atomic preservation, numeric edge cases and ISO timestamp validation.
- [x] Run `python -m unittest tests.test_sensor -v` and confirm failures are caused by missing production module.
- [x] Implement the minimal domain classes and rerun until green.

### Task 2: MonitoringManager

**Files:** Create `monitoring_manager.py`; test `tests/test_monitoring_manager.py`.

**Consumes:** `Sensor`; **Produces:** five manager APIs from the handoff.

- [x] Write failing tests for registration, duplicate/type rejection, ID validation, non-normalized lookup, removal, independent returned list, complete ordered snapshot and propagated reading exception.
- [x] Run the focused suite and verify RED.
- [x] Implement dictionary-backed registry and rerun focused plus existing tests.

### Task 3: Application Orchestrator and configuration

**Files:** Create `config.py`, `main.py`; test `tests/test_main.py`.

**Consumes:** manager plus injected simulation, alert, statistics and display contracts; **Produces:** deterministic timestamp helper, event processing and `run_simulation` coordination.

- [x] Write failing tests for deterministic timestamps, READING accept/reject, missing sensor, DISCONNECT, valid/invalid RECOVER, INVALID_DATA, stale-data protection, alert/stat/display routing.
- [x] Verify RED before production implementation.
- [x] Implement only orchestration and TV1 defaults; rerun all tests.

### Task 4: TV1 documentation

**Files:** Create `docs/TV1_HANDOFF.md`.

- [x] Document API, schemas, validation, exceptions, class/sequence diagrams, per-member integration instructions, complexity and known blockers.
- [x] Verify Markdown content against Master Handoff and comment/docstring language policy.

### Task 5: Quality gates and delivery

- [x] Run `python -m unittest discover -s tests -v`, `python -m compileall`, import smoke checks, `git diff --check`, ownership audit and secret/generated-file audit.
- [x] Inspect every diff; stage only TV1 files with explicit paths.
- [ ] Run cached-diff checks, commit, push the TV1 branch, and verify local/remote SHA and uploaded files.

## Review Focus

- Reject `bool` even though it is a subclass of `int`.
- Preserve the previous measurement on every failed validation or inactive update.
- Keep exact ID strings; whitespace-only is invalid but surrounding whitespace is not silently stripped.
- Never evaluate a snapshot or a failed update as a new environmental reading.
- RECOVER changes only `ERROR` sensors to `ACTIVE`; it never activates `INACTIVE` sensors.
