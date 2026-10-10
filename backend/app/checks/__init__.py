from ..models import CheckResult, Evidence
from ..serp import Hit


def result(id, title, weight, status, finding, *, engine=None, query=None, evidence=(), flags=(), **meta):
    return CheckResult(id=id, title=title, weight=weight, status=status, finding=finding, engine=engine,
                       query=query, evidence=list(evidence)[:5], flags=list(flags), meta=meta)


def ev(hit: Hit, title: str, url: str, snippet: str = "") -> Evidence:
    return Evidence(title=title or url, url=url, snippet=snippet or "", retrieved_at=hit.retrieved_at,
                    from_cache=hit.from_cache)
