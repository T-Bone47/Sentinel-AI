"""
M2's LANL window selection and measures on a hand-made miniature of the data
(no LANL download needed). The registered rules being checked are in
research/M2_PREREGISTRATION.md §5 and §6.
"""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "research" / "scripts"))
import lanl_extract as lanl  # noqa: E402
import run_lanl_benchmark as bench  # noqa: E402


def _gz(path: Path, lines: list[str]) -> Path:
    path.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode("ascii")))
    return path


def test_lanl_windows_draws_and_measures_follow_the_registration(tmp_path):
    # One red-team record (twice in the file): U1 from C1 to C2 at t = 10000.
    # Window [6400, 13600), scoring region [8200, 13600).
    red = _gz(tmp_path / "redteam.txt.gz", ["10000,U1@DOM1,C1,C2", "10000,U1@DOM1,C1,C2"])
    auth = _gz(tmp_path / "auth.txt.gz", [
        "6399,U1@DOM1,U1@DOM1,C1,C9,?,Network,LogOn,Success",       # 1  before the window
        "6400,U1@DOM1,U1@DOM1,C1,C9,?,Network,LogOn,Fail",          # 2  first second of the window
        "9000,U1@DOM1,U1@DOM1,C1,C9,Kerberos,?,TGT,Fail",           # 3  a failure in the 30 minutes before
        "9500,U2@DOM1,U2@DOM1,C3,C4,?,Network,LogOn,Success",       # 4-7 comparison candidates
        "9600,U3@DOM1,U3@DOM1,C3,C4,?,Network,LogOn,Success",
        "9700,U4@DOM1,U4@DOM1,C3,C4,?,Network,LogOn,Fail",
        "9800,U5@DOM1,U5@DOM1,C3,C4,?,Network,LogOn,Success",
        "9900,U6@DOM1,U6@DOM1,C3,C4,?,Network,LogOff,Success",      # 8  no LogOn: not a candidate
        "9950,C7$@DOM1,C7$@DOM1,C3,C4,?,Network,LogOn,Success",     # 9  not a user account
        "10000,U1@DOM1,U1@DOM1,C1,C2,NTLM,Network,LogOn,Success",   # 10 the red-team sign-in
        "10000,U1@DOM1,U1@DOM1,C1,C2,NTLM,Network,LogOff,Success",  # 11 also matches; not a sign-in
        "13599,U1@DOM1,U1@DOM1,C1,C9,?,Network,LogOn,Success",      # 12 last second of the window
        "13600,U1@DOM1,U1@DOM1,C1,C9,?,Network,LogOn,Success",      # 13 after it
    ])
    records, lines = lanl.read_redteam(red)
    assert (records, lines) == ([(10000, "U1@DOM1", "C1", "C2")], 2)

    extraction = lanl.extract(auth, records)
    assert extraction == lanl.extract(auth, records)                     # the seeded draw repeats
    rt, cmp = ([s for s in extraction["sources"] if s["kind"] == kind] for kind in ("rt", "cmp"))
    assert [n for n, _ in rt[0]["lines"]] == [2, 3, 10, 11, 12]
    assert extraction["candidates"] == [4] and len(extraction["draws"][0]) == 3
    assert set(extraction["draws"][0]) < {"U2@DOM1", "U3@DOM1", "U4@DOM1", "U5@DOM1"}
    assert sorted(s["account"] for s in cmp) == sorted(extraction["draws"][0])
    assert all(len(s["lines"]) == 1 for s in cmp)

    for source in extraction["sources"]:
        source["excluded"] = False
    def alert(source, line):
        return {"rule_id": "IA-003", "source_id": source["id"], "events": [{"role": "trigger", "source_event_id": str(line)}]}
    hit, stray, false = alert(rt[0], 10), alert(rt[0], 12), alert(cmp[0], cmp[0]["lines"][0][0])
    scored = {"alerts": [hit, stray, false], "ingested": {}, "not_evaluable": {}, "runs": 3}
    metrics, rows, alerts = bench.measure(records, lines, extraction, scored)

    assert rows == [{"record": 1, "class": "c", "matched_lines": [10, 11], "evaluable_lines": [10],
                     "failures_before": 1, "detected": True}]
    assert metrics["primary"]["strict_recall"]["recall"] == 1.0
    successes = sum(s["lines"][0][1].endswith("LogOn,Success") for s in cmp)
    rate = metrics["primary"]["comparison_alert_rate"]
    assert (rate["alerts"], rate["windows"], rate["successful_logons"]) == (1, 3, successes)
    assert metrics["secondary"]["ia003_unlabelled_alerts_on_red_team_accounts"] == 1
    assert [a["label"] for a in alerts] == ["comparison", "red-team", "unlabelled"]    # sorted by trigger line
