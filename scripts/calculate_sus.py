#!/usr/bin/env python3
"""Calculate SUS; input origin is preserved in the output. Python 3, stdlib only."""
import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def contributions(answers):
    if not isinstance(answers, list) or len(answers) != 10:
        raise ValueError("Each response must contain exactly 10 answers")
    if any(type(x) is not int or not 1 <= x <= 5 for x in answers):
        raise ValueError("Answers must be integers in the range 1..5")
    return [x - 1 if i % 2 == 0 else 5 - x for i, x in enumerate(answers)]

def score(answers):
    return sum(contributions(answers)) * 2.5

def summarize(data):
    rows = data.get("responses")
    if not isinstance(rows, list) or not rows:
        raise ValueError("At least one complete response is required")
    seen = set()
    calculated = []
    for row in rows:
        participant = row.get("participant_id")
        if not isinstance(participant, str) or not participant or participant in seen:
            raise ValueError("Participant IDs must be nonempty and unique")
        seen.add(participant)
        c = contributions(row.get("answers"))
        calculated.append({"participant_id": participant, "contributions": c,
                           "sum": sum(c), "sus": sum(c) * 2.5})
    scores = [r["sus"] for r in calculated]
    return {"data_kind": data.get("data_kind", "unspecified"),
            "notice": data.get("notice", ""), "object": data.get("object", ""),
            "date": data.get("date"), "participants": calculated,
            "count": len(scores), "mean": statistics.mean(scores),
            "median": statistics.median(scores), "minimum": min(scores),
            "maximum": max(scores), "range": max(scores)-min(scores),
            "score_is_percentage": False}

def self_test():
    assert score([5,1]*5) == 100
    assert score([1,5]*5) == 0
    assert score([3]*10) == 50
    sample = [4,2,4,2,3,3,4,2,4,2]
    assert score(sample) == 70
    for answers in ([5,1]*5, [1,5]*5, [3]*10, sample):
        assert score(answers) == (sum(answers[::2]) - sum(answers[1::2]) + 20)*2.5
    for bad in ([3]*9, [0]+[3]*9, [6]+[3]*9, [3.0]*10, [True]*10):
        try:
            score(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid response was accepted")
    try:
        summarize({"responses":[{"participant_id":"P1","answers":[3]*10},
                                {"participant_id":"P1","answers":[3]*10}]})
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate participant was accepted")
    print("SUS self-test: OK")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT/"data/sus-model.json")
    parser.add_argument("--output", type=Path, default=ROOT/"data/sus-summary.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Origin: {result['data_kind']}; n={result['count']}; "
          f"mean={result['mean']:g}; median={result['median']:g}; "
          f"range={result['minimum']:g}..{result['maximum']:g}")

if __name__ == "__main__":
    main()
