"""Core check: does the sender's email domain belong to the company the offer claims to be from?"""
import re

from ..extract import FREE_MAIL, core_tokens
from . import ev, result

ID, TITLE, WEIGHT, ENGINE = "sender_identity", "Sender identity", 30, "google"

ATS = ("lever.co", "greenhouse.io", "myworkdayjobs.com", "darwinbox.in", "darwinbox.com", "keka.com", "freshteam.com")
SKIP_SITES = {
    "linkedin", "glassdoor", "ambitionbox", "indeed", "naukri", "internshala", "justdial", "wikipedia",
    "facebook", "instagram", "x", "twitter", "youtube", "zaubacorp", "tofler", "quora", "reddit",
}
# Mail domains often differ from the website; the live search is still run and cited. Add rows as needed.
SEED = {
    "tcs": ["tcs.com"], "tata consultancy": ["tcs.com"], "infosys": ["infosys.com"], "wipro": ["wipro.com"],
    "hcl": ["hcltech.com", "hcl.com"], "hcltech": ["hcltech.com"], "tech mahindra": ["techmahindra.com"],
    "cognizant": ["cognizant.com"], "accenture": ["accenture.com"], "capgemini": ["capgemini.com"],
    "ibm": ["ibm.com"], "amazon": ["amazon.com", "amazon.jobs"], "google": ["google.com"],
    "microsoft": ["microsoft.com"], "deloitte": ["deloitte.com"], "ey": ["ey.com"], "pwc": ["pwc.com"],
    "kpmg": ["kpmg.com"], "zoho": ["zoho.com", "zohocorp.com"], "flipkart": ["flipkart.com"],
    "ltimindtree": ["ltimindtree.com"],
}
_TWO_PART = {"co", "com", "org", "net", "ac", "gov", "edu", "nic", "res"}


def host_of(s: str) -> str:
    s = s.lower().strip()
    s = s.split("@")[-1] if "@" in s else re.sub(r"^https?://", "", s).split("/")[0]
    return s.removeprefix("www.")


def registrable(host: str) -> str:
    p = host_of(host).split(".")
    if len(p) >= 3 and len(p[-1]) == 2 and p[-2] in _TWO_PART:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def label(domain: str) -> str:
    return registrable(domain).split(".")[0]


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_lookalike(sender_domain: str, official_domain: str) -> bool:
    s, o = registrable(sender_domain), registrable(official_domain)
    if s == o:
        return False
    sl, ol = label(s), label(o)
    if sl == ol:  # tcs.in vs tcs.com
        return True
    if len(ol) >= 5 and levenshtein(sl, ol) <= (1 if len(ol) < 8 else 2):
        return True
    if ol in sl.split("-") or (len(ol) >= 5 and ol in sl):  # tcs-careers-india.in, infosysrecruitment.com
        return True
    host = host_of(sender_domain)
    return o in host and not host.endswith(o)  # tcs.com.evil.in


def _matches(sd: str, domains: list[str]) -> bool:
    return any(sd == registrable(o) or sd.endswith("." + registrable(o)) for o in domains)


def classify(sender_domain: str, official: list[str], trusted: list[str] | None = None) -> tuple[str, str, dict]:
    """-> (status, reason, meta). Pure, so it is unit-testable without search.

    `trusted` is the subset of `official` confirmed by the knowledge panel or the known-company
    list (None = treat all as trusted). Only a trusted match can pass.
    """
    sd = host_of(sender_domain)
    if _matches(sd, official if trusted is None else trusted):
        return "pass", f"The sender's domain ({sd}) matches the company's official domain.", {}
    if _matches(sd, official):
        return "warn", "The sender matches the top search result for this company, but we couldn't confirm that site is official.", {"untrusted_match": True}
    if registrable(sd) in FREE_MAIL:
        return "fail", f"The offer was sent from a free mail address ({sd}), not the company's own domain ({official[0]}).", {"free_mail": True}
    for o in official:
        if is_lookalike(sd, o):
            return "fail", f"The sender's domain ({sd}) imitates the official domain {o}.", {"lookalike": True, "lookalike_of": o}
    if any(sd == a or sd.endswith("." + a) for a in ATS):
        return "warn", f"The sender uses a hiring-platform domain ({sd}); anyone can create pages there, so this proves nothing.", {}
    return "warn", f"The sender's domain ({sd}) is not the company's official domain ({official[0]}).", {"third_party": True, "sender_domain": sd}


def _seed(company: str) -> list[str]:
    return SEED.get(" ".join(core_tokens(company)), [])


def find_official(ctx, serp):
    """-> (domains, query, evidence, trusted). Seed domains are aliases; the search result is always cited.

    `trusted` = knowledge-panel website + known-company list. A domain found only as a top organic
    result is a guess (a scam's own site can rank first), so it is never shown to users as official.
    """
    query = f"{ctx.company} official website"
    hit = serp.search({"engine": "google", "q": query})
    toks = core_tokens(ctx.company)
    found, evidence, trusted = [], [], list(_seed(ctx.company))
    site = (hit.data.get("knowledge_graph") or {}).get("website")
    if site:
        found.append(registrable(site))
        trusted.insert(0, registrable(site))
        evidence.append(ev(hit, "Knowledge panel: official website", site))
    else:
        for r in hit.data.get("organic_results", []):
            d = registrable(r.get("link", ""))
            lab = d.split(".")[0]
            if lab in SKIP_SITES:
                continue
            if any(t == lab or (len(t) >= 4 and (t in lab or lab in t)) for t in toks):
                found.append(d)
                evidence.append(ev(hit, r.get("title", d), r["link"], r.get("snippet", "")))
                break
    return list(dict.fromkeys(found + _seed(ctx.company))), query, evidence, list(dict.fromkeys(trusted))


def run(ctx, serp):
    if not ctx.company:
        return result(ID, TITLE, WEIGHT, "unknown", "Couldn't tell which company the offer claims to be from.", engine=ENGINE)
    try:
        official, query, evidence, trusted = find_official(ctx, serp)
    except Exception:
        official, query, evidence, trusted = _seed(ctx.company), None, [], _seed(ctx.company)  # search down: seed still lets us judge
        if not official:
            raise
    if not official:
        return result(ID, TITLE, WEIGHT, "unknown", f"Couldn't find an official website for {ctx.company}.", engine=ENGINE, query=query, evidence=evidence)
    if not ctx.sender_email:
        return result(ID, TITLE, WEIGHT, "unknown",
                      "No sender email in the message — most WhatsApp/Telegram offers have none, so this can't be verified.",
                      engine=ENGINE, query=query, evidence=evidence, official=official, trusted=trusted)
    status, reason, meta = classify(ctx.sender_email, official, trusted)
    return result(ID, TITLE, WEIGHT, status, reason, engine=ENGINE, query=query, evidence=evidence,
                  official=official, trusted=trusted, company=ctx.company, known_brand=bool(_seed(ctx.company)), **meta)
