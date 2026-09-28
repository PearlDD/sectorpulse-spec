# Factory Configuration

## Goal

AI-powered sector rotation analytics web app using Claude agents to analyze macroeconomic conditions, score market sectors, generate portfolio allocations, and deliver visual dashboards with RRG charts.

## Scope

### Modifiable

- backend/app/**/*.py
- backend/tests/**/*.py
- frontend/src/**/*.tsx
- frontend/src/**/*.ts
- frontend/src/**/*.css
- eval/score.py

### Read-only

- README.md
- CLAUDE.md
- backend/pyproject.toml
- frontend/package.json
- .env.example

## Guards

- Do not delete or overwrite existing tests
- Do not modify files outside the declared scope
- Do not introduce secrets or credentials into the repository
- Do not pass current dates to agent prompts (anti-look-ahead-bias rule)
- Do not switch agents back to claude-opus-4-6 — use claude-sonnet-4-6

## Eval

### Command

```bash
python3 eval/score.py
```

### Threshold

0.6

## Smoke Test

```bash
cd backend && python3 -c "import uvicorn,threading,time,urllib.request; t=threading.Thread(target=lambda:uvicorn.run('app.main:app',host='127.0.0.1',port=18765,log_level='warning'),daemon=True); t.start(); time.sleep(3); r=urllib.request.urlopen('http://127.0.0.1:18765/api/health'); assert r.status==200; print('PASS')"
```

## Target Branch

main
