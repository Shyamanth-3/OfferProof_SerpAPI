from ..models import CheckResult, Evidence
from ..serp import Hit


def result(id, title, weight, status, finding, *, engine=None, query=None, evidence=(), flags=(), phrases=(), **meta):
    return CheckResult(id=id, title=title, weight=weight, status=status, finding=finding, engine=engine,
                       query=query, evidence=list(evidence)[:5], flags=list(flags), phrases=list(phrases), meta=meta)


def ev(hit: Hit, title: str, url: str, snippet: str = "", kind: str | None = None) -> Evidence:
    return Evidence(title=title or url, url=url, snippet=snippet or "", retrieved_at=hit.retrieved_at,
                    from_cache=hit.from_cache, kind=kind)
