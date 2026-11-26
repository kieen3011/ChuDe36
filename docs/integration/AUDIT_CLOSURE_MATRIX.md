# Audit Closure Matrix

| ID | Phase 0 finding | Closure | Evidence |
|---|---|---|---|
| INT-01 | TV2 thiếu `generate_events` | CLOSED | `SimulationAdapter.generate_events`; real E2E PASS |
| INT-02 | TV3 evaluate signature mismatch | CLOSED | `AlertAdapter.evaluate(reading)`; contract test PASS |
| INT-03 | Alert schema mismatch | CLOSED | Canonical 7-field Alert Record; TV4 accepts |
| INT-04 | `error_count`/`total_errors` mismatch | CLOSED | Non-mutating compatibility view |
| INT-05 | `A` và `Khu A` mismatch | CLOSED | Central `ZONE_LABELS`; core IDs A/B/C |
| INT-06 | main thiếu entry point | CLOSED | `main()` và `if __name__`; CLI exit 0 |
| INT-07 | `statistics.py` shadowing | CLOSED | Renamed `statistics_tracker.py`; stdlib mean PASS |
| INT-08 | Chỉ có mock orchestrator tests | CLOSED | 5 deterministic/real E2E tests |
| INT-09 | Threshold/boundary sai | CLOSED | Boundary matrix và exact delta tests PASS |
| INT-10 | NORMAL/error bị coi là alert | CLOSED | AlertAdapter returns None hoặc Alert Record |
| INT-11 | Dedup poisoning | CLOSED | Validation trước `_seen_keys`; regression PASS |
| INT-12 | pytest dependency không khai báo | CLOSED | 6 TV4 tests chuyển sang unittest |
| INT-13 | bool được TV3 chấp nhận | CLOSED | TV3 từ chối bool/non-finite |
| INT-14 | Handoff lỗi thời | CLOSED | README/handoff cập nhật Phase 2 |
| INT-15 | NaN trong Statistics/JSON | CLOSED | finite validation và `allow_nan=False` |
| INT-16 | Lifecycle E2E bị blocked | CLOSED PHASE 3B | Recovery pending được đánh dấu stale; reading mới khôi phục freshness |

Tất cả finding Phase 0 có test hoặc runtime evidence. Không finding nào được đóng chỉ dựa trên code inspection.

## Phase 3A remediation closure

| ID | Finding | Closure | Evidence |
|---|---|---|---|
| REV-01 | Export fallback có thể corrupt destination | CLOSED | Fail-closed replace tests cho CSV/JSON |
| REV-02 | CLI chưa trình diễn environmental alerts | CLOSED | `--mode demo` qua production pipeline |
| REV-03 | Reading cũ hiển thị NORMAL sau RECOVER | CLOSED | Freshness lifecycle regression tests |
| REV-04 | Dữ liệu demo giống định danh cá nhân | CLOSED CURRENT TREE | Dùng `CHUDE36-DEMO`; lịch sử Git không bị rewrite |
| REV-05 | Release completeness | CLOSED | Release checklist và stage list đầy đủ |
| NEW-01 | Shared mutable thresholds | CLOSED | Deep-copy default/caller config và session tests |
| NEW-02 | CP1252 UnicodeEncodeError | CLOSED | Redirected subprocess tests |
| NEW-03 | Thiếu regression coverage | CLOSED | Dedicated Phase 3B regression suite |
