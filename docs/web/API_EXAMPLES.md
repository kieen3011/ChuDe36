# API Examples

Khoi dong local:

```powershell
.\.venv\Scripts\python.exe -m uvicorn web_api.app:app --host 127.0.0.1 --port 8000
```

Health va config:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/config
```

Random:

```powershell
$body = @{mode='random'; seed='sample-01'; step_count=10; step_interval_seconds=60} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/simulations/run -ContentType application/json -Body $body
```

Demo:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/simulations/run -ContentType application/json -Body '{"mode":"demo"}'
```

Swagger UI: `http://127.0.0.1:8000/docs`.

Demo response co `summary.total_alerts=4`, `warning_count=2`, `critical_count=2`, `error_count=2`. Frontend can giu `timeline` trong browser de play/pause/replay ma khong goi lai backend.
