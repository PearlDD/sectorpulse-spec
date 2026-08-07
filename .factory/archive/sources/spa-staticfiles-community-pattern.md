---
tags:
  - factory
  - source
  - sectorpulse
source: factory-archivist
date: 2026-08-07
---

# SPAStaticFiles Community Pattern (Starlette/FastAPI)

## Finding

The most common community solution for serving SPAs from FastAPI/Starlette is to subclass `StaticFiles` and override either `get_response` or `lookup_path` to fall back to `index.html`.

### `lookup_path` override (simpler)

```python
class SPAStaticFiles(StaticFiles):
    async def lookup_path(self, path):
        full_path, stat_result = await super().lookup_path(path)
        if stat_result is None:
            return await super().lookup_path("./index.html")
        return full_path, stat_result
```

### `get_response` override (more explicit error handling)

```python
class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise
```

## Trade-offs

- `lookup_path` is simpler but less precise on content-type handling
- `get_response` gives more control but catches exceptions which is slightly less clean
- Both are well-tested in production across the community

## References

- [Serving SPAs from Starlette](https://www.crccheck.com/blog/serving-spas-from-starlette/)
- [Serving React with FastAPI](https://davidmuraya.com/blog/serving-a-react-frontend-application-with-fastapi/)
