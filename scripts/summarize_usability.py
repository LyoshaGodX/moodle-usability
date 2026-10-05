#!/usr/bin/env python3
"""Summarize observed or model trials without merging independent/assisted success."""
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def summarize(data):
    participants = {p["id"] for p in data["participants"]}
    tasks = {t["id"]: t for t in data["tasks"]}
    rows = data["trials"]
    if not participants or not tasks or len(rows) != len(participants)*len(tasks):
        raise ValueError("A complete participant-by-task matrix is required")
    pairs = set()
    for r in rows:
        p, t = r["participant_id"], r["task_id"]
        if p not in participants or t not in tasks or (p,t) in pairs:
            raise ValueError("Unknown or duplicate participant-task pair")
        pairs.add((p,t))
        seconds, errors = r["seconds"], r["navigation_errors"]
        if type(seconds) not in (int, float) or not 0 < seconds <= tasks[t]["limit_seconds"]:
            raise ValueError("Trial duration is outside the task limit")
        if type(errors) is not int or errors < 0:
            raise ValueError("Navigation errors must be nonnegative integers")
        if r["status"] not in ("success","assisted","failed"):
            raise ValueError("Unknown status")
        if r["status"] == "failed" and seconds != tasks[t]["limit_seconds"]:
            raise ValueError("Failed trials in this protocol stop at the time limit")
        if r.get("data_kind") != data.get("data_kind"):
            raise ValueError("Mixed data origins")
    counts = {s:sum(r["status"] == s for r in rows) for s in ("success","assisted","failed")}
    per_task = []
    for t in tasks:
        subset = [r for r in rows if r["task_id"] == t]
        independent = [r["seconds"] for r in subset if r["status"] == "success"]
        per_task.append({"task_id":t, "count":len(subset),
                         **{s:sum(r["status"]==s for r in subset) for s in counts},
                         "mean_attempt_seconds":statistics.mean(r["seconds"] for r in subset),
                         "mean_independent_seconds":statistics.mean(independent) if independent else None,
                         "navigation_errors":sum(r["navigation_errors"] for r in subset)})
    return {"data_kind":data["data_kind"], "notice":data["notice"], "date":data["date"],
            "attempts":len(rows), "counts":counts,
            "percentages":{s:n/len(rows)*100 for s,n in counts.items()},
            "completed_including_assistance":counts["success"]+counts["assisted"],
            "completion_including_assistance_percent":(counts["success"]+counts["assisted"])/len(rows)*100,
            "navigation_errors":sum(r["navigation_errors"] for r in rows),
            "per_task":per_task}

if __name__ == "__main__":
    result = summarize(json.loads((ROOT/"data/usability-model.json").read_text(encoding="utf-8")))
    (ROOT/"data/usability-summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Origin: {result['data_kind']}; attempts={result['attempts']}; "
          f"independent={result['percentages']['success']:g}%; "
          f"assisted={result['percentages']['assisted']:g}%; "
          f"failed={result['percentages']['failed']:g}%")
