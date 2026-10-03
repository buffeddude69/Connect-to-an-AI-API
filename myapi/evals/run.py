import json 
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
CASES_PATH = Path(__file__).resolve().parent / "cases.json"

def main():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    matched = 0
    failures = []

    for case in cases:
        response = requests.post(
            f"{BASE_URL}/classify",
            json={"text": case["text"]},
            timeout=35,
        )

        if response.status_code != 200:
            failures.append({
                "text": case["text"],
                "expected": case["expected_category"],
                "actual": f"HTTP {response.status_code}",
            })

            continue

        result = response.json()
        actual = result["category"]
        expected = case["expected_category"]

        if actual == expected:
            matched += 1

        else:
            failures.append({
                "text": case["text"],
                "expected": expected,
                "actual": actual,
            })

    total = len(cases)
    percentage = (matched / total) * 100

    print(f"Matched: {matched}/{total}")
    print(f"Category accuracy: {percentage:.1f}%")

    if failures:
        print("\nFailed cases:")

        for failure in failures:
            print(f"- {failure['text']}")
            print(
                f" expected={failure['expected']}, "
                f" actual={failure['actual']}"
            )

if __name__ == "__main__":
    main()