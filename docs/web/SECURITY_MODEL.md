# Security Model Candidate

## 1. Trust boundary

Moi HTTP input la khong tin cay. API chi cho phep simulation configuration, khong cho path, Python expression, module name, callback URL hoac serialized object.

## 2. Validation va resource limits

- Pydantic models dat `extra="forbid"`.
- Mode dung enum; seed gioi han 128 ky tu va khong dung lam file name.
- Step count public 1..100; interval 0.001..3600 giay simulated.
- Custom thresholds bi tu choi; bool, NaN, infinity va extra field bi tu choi.
- App body limit 64 KiB; chunked body dung doc ngay khi vuot limit.
- Benchmark noi bo gom 500 steps; public response lon nhat duoc do tai 100 steps.
- Khong sleep theo interval, khong background loop, khong subprocess.

## 3. Isolation va concurrency

- Object graph moi cho tung request.
- Khong global mutable session, cache hay threshold dictionary.
- Khong local filesystem session storage.
- Khong co app semaphore trong MVP; platform rate limit/capacity guard duoc defer.

Stateless isolation bao ve tinh dung dan, nhung khong thay the platform rate limiting. Public deployment can gateway/WAF rate limit neu traffic thuc te can.

## 4. CORS

- Development: chi origin frontend local duoc cau hinh.
- Production: explicit HTTPS frontend origins tu environment configuration.
- Khong dung wildcard khi credentials bat; MVP khong can cookie credential.
- Allow methods: GET, POST, OPTIONS. Allow headers toi thieu: Content-Type, Accept, X-Request-ID neu dung.

FastAPI `CORSMiddleware` co default han che va can khai bao origin ro rang; xem [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/).

## 5. Error va logging

- Response khong chua stack trace, local path, environment variable hay raw exception.
- Log request ID, endpoint, mode, step count, duration, status code; khong log full seed/threshold neu khong can.
- Khong log credentials. MVP khong can credentials.
- Validation error co field/reason da sanitize.

## 6. Dependency va supply chain

- Runtime pin trong `requirements.txt`; HTTPX test pin trong `requirements-dev.txt`.
- Chi them dependency can thiet; quet known vulnerabilities trong CI neu CI duoc cau hinh.
- Khong auto-install o Phase 4A.

## 7. HTTP hardening candidate

- HTTPS do hosting cung cap.
- `Content-Type` ro rang; `X-Content-Type-Options: nosniff`.
- Cache-Control: `no-store` cho simulation response neu chua co privacy/cache policy.
- Health/config co the cache ngan han sau khi danh gia.
- OpenAPI docs bat mac dinh cho development/academic demo, co environment switch de tat.
