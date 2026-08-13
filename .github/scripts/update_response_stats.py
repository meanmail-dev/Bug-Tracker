"""Recalculate issue response statistics and write them into README.md.

Usage: python3 update_response_stats.py <issues.json> <README.md>

The issues file is the output of:
    gh issue list --state all --limit 500 \
        --json number,createdAt,closedAt,state,author,comments
"""

import json
import statistics
import sys
from datetime import datetime, timedelta, timezone

START = "<!-- response-stats:start -->"
END = "<!-- response-stats:end -->"
WINDOW = timedelta(days=365)


def parse(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def hours_to_first_reply(issue):
    """Hours until someone other than the reporter replied, or None."""
    reporter = issue["author"]["login"]
    replies = [c for c in issue["comments"] if c["author"]["login"] != reporter]
    if not replies:
        return None
    first = min(parse(c["createdAt"]) for c in replies)
    return (first - parse(issue["createdAt"])).total_seconds() / 3600


def hours_to_close(issue):
    if not issue["closedAt"]:
        return None
    return (parse(issue["closedAt"]) - parse(issue["createdAt"])).total_seconds() / 3600


def humanize(hours):
    if hours < 1:
        return "under an hour"
    if hours < 48:
        value = round(hours)
        return f"{value} hour" if value == 1 else f"{value} hours"
    value = round(hours / 24)
    return f"{value} day" if value == 1 else f"{value} days"


def render(issues, today):
    recent = [i for i in issues if parse(i["createdAt"]) >= today - WINDOW]
    if not recent:
        return "Not enough data yet — this table fills in as issues come in."

    replies = [h for h in map(hours_to_first_reply, recent) if h is not None]
    closes = [h for h in map(hours_to_close, recent) if h is not None]
    closed = sum(1 for i in recent if i["state"] == "CLOSED")

    first_reply = humanize(statistics.median(replies)) if replies else "—"
    time_to_close = humanize(statistics.median(closes)) if closes else "—"

    return (
        "| Typical first reply | Typical time to a fix | Issues resolved |\n"
        "|:---:|:---:|:---:|\n"
        f"| **{first_reply}** | **{time_to_close}** | **{closed} of {len(recent)}** |\n"
        "\n"
        f"<sub>Median over the last 12 months, across {len(recent)} issues. "
        f"Updated automatically on {today:%d %B %Y}.</sub>"
    )


def main():
    issues_path, readme_path = sys.argv[1], sys.argv[2]

    with open(issues_path) as f:
        issues = json.load(f)

    with open(readme_path) as f:
        readme = f.read()

    if START not in readme or END not in readme:
        sys.exit(f"{readme_path} has no {START} / {END} markers")

    head, _, rest = readme.partition(START)
    _, _, tail = rest.partition(END)

    updated = (
        f"{head}{START}\n{render(issues, datetime.now(timezone.utc))}\n{END}{tail}"
    )

    with open(readme_path, "w") as f:
        f.write(updated)


if __name__ == "__main__":
    main()
