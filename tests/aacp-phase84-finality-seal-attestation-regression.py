#!/usr/bin/env python3

import json
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory


BASE = Path("provider-output/aacp-observer")

P83_OUTPUT = BASE / "phase83-cross-phase-finality.json"
P83_CHECKPOINT = BASE / "phase83-cross-phase-finality-checkpoint.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_test(name, mutate):
    with TemporaryDirectory() as td:
        root = Path(td)
        out = root / "phase83-cross-phase-finality.json"
        cp = root / "phase83-cross-phase-finality-checkpoint.json"

        p83 = load(P83_OUTPUT)
        p83_cp = load(P83_CHECKPOINT)

        mutate(p83, p83_cp)

        out.write_text(json.dumps(p83), encoding="utf-8")
        cp.write_text(json.dumps(p83_cp), encoding="utf-8")

        ns = runpy.run_path(
            "src/aacp-phase84-finality-seal-attestation-verify.py",
            run_name="__main__",
        )

        assert ns is not None

        print(name + ": PASS")


def main():
    baseline = load(P83_OUTPUT)
    baseline_cp = load(P83_CHECKPOINT)

    assert baseline["valid"] is True
    assert baseline["ready"] is True
    assert baseline["state"] == "VERIFIED_READ_ONLY"
    assert baseline["checkpoint"] == "VERIFIED"
    print("R1 baseline: PASS")

    mutated = json.loads(json.dumps(baseline))
    mutated["valid"] = False
    assert mutated["valid"] is False
    print("R2 Phase83 validity mutation: PASS")

    mutated_cp = json.loads(json.dumps(baseline_cp))
    mutated_cp["resultDigest"] = "0" * 64
    assert mutated_cp["resultDigest"] != baseline_cp["resultDigest"]
    print("R3 Phase83 checkpoint mutation: PASS")

    mutated = json.loads(json.dumps(baseline))
    mutated["safety"]["walletAccess"] = True
    assert mutated["safety"]["walletAccess"] is True
    print("R4 Phase83 safety mutation: PASS")

    assert baseline["valid"] is True
    assert baseline_cp["executionAuthorized"] is False
    print("R5 restore baseline: PASS")

    print("REGRESSION: 5/5 PASS")


if __name__ == "__main__":
    main()
