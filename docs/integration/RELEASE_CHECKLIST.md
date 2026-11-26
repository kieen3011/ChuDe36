# Stable Python Core Release Checklist

- [x] Full unittest suite PASS, không fail/error/skip.
- [x] Compile và import checks PASS.
- [x] Default, random và demo CLI exit 0.
- [x] TV2/TV3 standalone demo PASS với UTF-8 và CP1252 redirect.
- [x] CSV/JSON strict parse và count invariants PASS.
- [x] Export fault injection giữ report cũ và cleanup temp.
- [x] Recovery pending không hiển thị stale measurement như NORMAL.
- [x] Hai application session không chia sẻ threshold state.
- [x] Standard-library `statistics` không bị shadow.
- [x] `git diff --check` PASS.
- [ ] Không stage output, cache, `.pyc` hoặc worktree metadata.
- [ ] Review chính xác modified, added và deleted files trước commit.
- [ ] Không thay đổi `main` hoặc `Kien`; không merge hoặc push khi chưa được duyệt.
