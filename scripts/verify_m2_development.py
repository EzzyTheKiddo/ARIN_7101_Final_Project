"""Read back the November 19 M2 archive and report the separate, live review status."""
import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from test_member_handoff import ROOT, load


def main():
    run = "m2_development_20261119"
    handoff = ROOT / "team_workspace" / "m2_handoff"
    with ZipFile(handoff / "m2_to_m4_20261123.zip") as package:
        assert package.testzip() is None
        archive = package.read(f"{run}.zip")
    digest = hashlib.sha256(archive).hexdigest()
    assert digest == "d37124517525f34223bc1cfe89cc11fb420689cca6b83237c187fb095e3cf5ba"
    notebook = "ARIN7101_Context_Bandit_Release_Notebook.ipynb"
    with ZipFile(BytesIO(archive)) as z:
        assert z.testzip() is None
        snapshot = z.read(f"{run}/source/{notebook}")
        assert hashlib.sha256(snapshot).hexdigest() == "0bad1685c2cebf7cd1112e117e7f88afe51297ffc88cb1b40ca57eb8482bcff3"
        rows = pd.read_csv(BytesIO(z.read(f"{run}/tables/development_outcomes.csv")))
        for item in ("tables/m3_handoff_abrupt_130100.csv", "tables/strategy_by_query.csv",
                     "audit/audit_examples.json", "audit/strategy_checks.json"):
            # Text files in Git may be checked out with different line endings.
            local = (handoff / Path(item).name).read_text(encoding="utf-8")
            assert local == z.read(f"{run}/{item}").decode().replace("\r\n", "\n"), item

    ns = load(ROOT / notebook, "m2")
    cfg = ns["PROTOCOL_DRAFT"]
    episodes = [ns["generate_episode"](seed, scenario, cfg)
                for scenario, first in (("stable", 130000), ("abrupt", 130100))
                for seed in range(first, first + 3)]
    assert len(rows) == 7200 and all(ns["audit_truth"](ep)["passed"] for ep in episodes)
    ns["m2_validate_development_outcomes"](episodes, rows, cfg)
    grouped = rows.groupby(["scenario", "state", "qtype", "arm"], as_index=False).agg(
        n_questions=("y", "size"), accuracy=("y", "mean"), mean_cost=("cost", "mean"),
        mean_utility=("utility", "mean"), coverage_rate=("coverage", "mean"),
        outdated_rate=("outdated", "mean"), mean_construction_ms=("construction_ms", "mean"))
    pd.testing.assert_frame_equal(grouped, pd.read_csv(handoff / "strategy_by_query.csv"))
    pd.testing.assert_frame_equal(rows[rows.seed == 130100].reset_index(drop=True),
                                  pd.read_csv(handoff / "m3_handoff_abrupt_130100.csv"))
    keys = ns["M2_DEVELOPMENT_AUDIT_KEYS"]
    rebuilt = ns["m2_build_audit_examples"](episodes, rows, cfg, keys)
    assert rebuilt == json.loads((handoff / "audit_examples.json").read_bytes())["questions"]
    case = next(q for q in rebuilt if (q["seed"], q["t"]) == (130100, 99))
    assert case["evidence"] == 323 and case["resolved_evidence_rank"] == 9
    review_path = handoff / "audit_review.csv"
    review = pd.read_csv(review_path, keep_default_na=False)
    assert list(review) == ["seed", "t", "m1_reviewer", "m2_reviewer", "verdict", "m1_notes", "m2_notes"]
    assert len(review) == len(keys) and set(zip(review.seed, review.t)) == set(keys)
    assert review.verdict.isin(["pending", "pass", "fail"]).all()
    notes_present = review[["m1_reviewer", "m1_notes", "m2_reviewer", "m2_notes"]].apply(
        lambda col: col.str.strip().ne(""))
    assert notes_present.loc[review.verdict.ne("pending")].all().all()
    print(f"{run}: {len(rows)} rows, 1800 questions, 40 reconstructed audit arms.")
    print("Review SHA-256:", hashlib.sha256(review_path.read_bytes()).hexdigest())
    print("Recorded verdicts:", review.verdict.value_counts().to_dict())


if __name__ == "__main__":
    main()
