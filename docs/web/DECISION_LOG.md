# Web Backend Decision Log

| ID | Decision | Status Phase 4B |
|---|---|---|
| DR-W01 | MVP chi dung approved thresholds; custom thresholds bi tu choi | IMPLEMENTED |
| DR-W02 | Public max 100 steps; benchmark internal 10/100/500 | IMPLEMENTED |
| DR-W03 | Frontend export tu response; khong co server export endpoint | IMPLEMENTED |
| DR-W04 | ASGI portable; Vercel chi la preview candidate, chua deploy | IMPLEMENTED |
| DR-W05 | Explicit CORS allowlist, khong credential | IMPLEMENTED |
| DR-W06 | OpenAPI bat mac dinh va co environment switch | IMPLEMENTED |
| WEB-01 | Moi request tao object graph core rieng | IMPLEMENTED |
| WEB-02 | Khong database, registry, background loop hoac shared file | IMPLEMENTED |
| WEB-03 | Frontend replay full timeline tai browser | IMPLEMENTED |
| WEB-04 | Reading Record bay field; freshness la wrapper metadata | IMPLEMENTED |

## Deferred decisions

- Custom thresholds can Product Owner phe duyet schema replacement va test moi.
- Server export endpoint chi them khi co API consumer cu the.
- Production hosting, rate limit/WAF, authentication va observability thuoc phase sau.
- Public step limit khong tang tu 100 chi dua tren benchmark local.

## Minimal core extension

Orchestrator co hook `record_step` tuy chon. Renderer cu khong can implement hook va tiep tuc hoat dong. Hook nhan actual events, accepted readings, step alerts, error slice va cumulative summary; vi vay backend khong suy luan lai business events. `StatisticsTracker` cung cap getter tra ban sao de collector khong doc private state.
