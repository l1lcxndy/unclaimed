"""Oracle and null checks: a perfect answer must pass every case, an empty answer must fail every case
that expects something. If either breaks, the eval's numbers can't be trusted."""
from evals.run_eval import grade, load_cases, program_names

KNOWN = program_names()


def oracle(case):
    return {"programs": [{"program_name": n, "cited": True} for n in case["expected"]],
            "missing_info": ["annual income"] if case.get("needs_info") else []}


def test_oracle_passes_every_case():
    failures = [c["id"] for c in load_cases() if grade(c, oracle(c), KNOWN)[0]["pass"] != 1]
    assert failures == []


def test_empty_answer_fails_every_case_that_expects_something():
    for case in load_cases():
        scores, _ = grade(case, {"programs": [], "missing_info": []}, KNOWN)
        should_fail = bool(case["expected"]) or case.get("needs_info")
        assert scores["pass"] == (0 if should_fail else 1), case["id"]


def test_wrong_invented_and_uncited_programs_fail():
    case = {"expected": ["Farm Income Support"], "forbidden": ["Senior Citizen Pension"]}
    farm = {"program_name": "Farm Income Support", "cited": True}
    assert grade(case, {"programs": [farm, {"program_name": "Senior Citizen Pension", "cited": True}]}, KNOWN)[0]["pass"] == 0
    assert grade(case, {"programs": [farm, {"program_name": "Moon Tax Refund", "cited": True}]}, KNOWN)[0]["pass"] == 0
    assert grade(case, {"programs": [{"program_name": "Farm Income Support", "cited": False}]}, KNOWN)[0]["pass"] == 0
    assert grade(case, {"programs": [farm]}, KNOWN)[0]["pass"] == 1
