"""Bounded, read-only GitHub enrichment, enabled explicitly by the user."""

import re

import httpx

from .models import Evidence


def enrich(remote: str, evidence: list[Evidence], token: str = "") -> tuple[list[Evidence], list[str]]:
    if not remote:
        return [], ["GitHub enrichment needs an origin remote on github.com."]
    slug = remote.removeprefix("https://github.com/")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    found: dict[str, Evidence] = {}
    warnings = []
    budget = 24

    with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=12) as client:
        def get(path: str):
            nonlocal budget
            if budget <= 0:
                raise ValueError("GitHub request budget reached; showing the sources retrieved so far.")
            budget -= 1
            response = client.get(path, params={"per_page": 30})
            response.raise_for_status()
            if 'rel="next"' in response.headers.get("link", ""):
                warnings.append("A GitHub discussion has more than 30 entries; only its first page was retrieved.")
            return response.json()

        def add(item: dict, kind: str, title: str = ""):
            url = item.get("html_url", "")
            # Do not make generated source links into arbitrary navigation targets.
            if not url.startswith(f"{remote}/"):
                return
            found[url] = Evidence(id=f"github:{item['id']}", kind=kind,
                title=title or item.get("title", "Discussion"), body=(item.get("body") or "")[:12000],
                url=url, date=item.get("created_at", ""))

        try:
            issues: set[int] = set()
            pulls: set[int] = set()
            for source in evidence[:5]:
                issues.update(int(n) for n in re.findall(r"(?<![\w/])#(\d+)", source.body))
                for pr in get(f"/repos/{slug}/commits/{source.sha}/pulls"):
                    number = pr["number"]
                    if number in pulls:
                        continue
                    pulls.add(number)
                    add(pr, "pull_request")
                    issues.update(int(n) for n in re.findall(r"(?<![\w/])#(\d+)", pr.get("body") or ""))
                    for comment in get(f"/repos/{slug}/issues/{number}/comments"):
                        add(comment, "comment", f"PR #{number} discussion")
                    for comment in get(f"/repos/{slug}/pulls/{number}/comments"):
                        add(comment, "comment", f"PR #{number} code review")
            for number in sorted(issues - pulls)[:8]:
                issue = get(f"/repos/{slug}/issues/{number}")
                add(issue, "pull_request" if "pull_request" in issue else "issue")
                for comment in get(f"/repos/{slug}/issues/{number}/comments"):
                    add(comment, "comment", f"Issue #{number} discussion")
        except httpx.HTTPStatusError as exc:
            warnings.append(f"GitHub returned HTTP {exc.response.status_code}; some discussions could not be retrieved.")
        except httpx.HTTPError:
            warnings.append("GitHub could not be reached; some discussions could not be retrieved.")
        except ValueError as exc:
            warnings.append(str(exc))
    if len(evidence) > 5:
        warnings.append("GitHub enrichment is limited to the five most recent line-changing commits.")
    return list(found.values()), list(dict.fromkeys(warnings))
