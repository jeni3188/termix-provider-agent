#!/usr/bin/env python3

import json
import subprocess
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE = (
    BASE_DIR
    / "src"
    / "aacp-evidence-chain-health-continuous-readiness-repeatability-verify.py"
)

OBSERVER = BASE_DIR / "provider-output" / "aacp-observer"

PHASE37 = (
    OBSERVER
    / "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json"
)

BASELINE = (
    OBSERVER
    / "aacp-evidence-chain-health-post-readiness-drift-baseline.json"
)

LAYERS = [
    OBSERVER / "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
    OBSERVER / "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
    OBSERVER / "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
    OBSERVER / "latest-aacp-evidence-chain-health-integrity-attestation.json",
    OBSERVER / "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
]


def run():
    return subprocess.run(
        ["python", str(SOURCE)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
    )


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def assert_blocked(label):
    result = run()
    assert result.returncode != 0, label
    output = load(
        OBSERVER
        / "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json"
    )
    assert output["state"] == "BLOCKED", label
    assert output["verification"]["valid"] is False, label
    print(f"PASS: {label}")


def main():
    original_phase37 = PHASE37.read_text(encoding="utf-8")
    original_baseline = BASELINE.read_text(encoding="utf-8")
    original_layers = [
        path.read_text(encoding="utf-8") for path in LAYERS
    ]

    try:
        result = run()
        assert result.returncode == 0
        output = load(
            OBSERVER
            / "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json"
        )
        assert output["state"] == "VERIFIED_READ_ONLY"
        assert output["readiness"]["ready"] is True
        assert output["verification"]["valid"] is True
        assert output["verification"]["verifiedLayers"] == 5
        print("PASS: baseline repeatability verifies")

        result = run()
        assert result.returncode == 0
        print("PASS: repeated execution remains verified")

        for index, path in enumerate(LAYERS):
            original = path.read_text(encoding="utf-8")
            data = json.loads(original)
            data["_regression_drift"] = index + 1
            save(path, data)
            assert_blocked(f"phase{31 + index} drift is blocked")
            path.write_text(original, encoding="utf-8")

        missing = LAYERS[0]
        original = missing.read_text(encoding="utf-8")
        missing.unlink()
        assert_blocked("missing phase31 artifact is blocked")
        missing.write_text(original, encoding="utf-8")

        original_baseline_data = load(BASELINE)
        original_baseline_data["type"] = "CORRUPTED_BASELINE"
        save(BASELINE, original_baseline_data)
        assert_blocked("corrupted baseline type is blocked")
        BASELINE.write_text(original_baseline, encoding="utf-8")

        phase37_data = load(PHASE37)
        phase37_data["readiness"]["ready"] = False
        save(PHASE37, phase37_data)
        assert_blocked("Phase37 not ready is blocked")
        PHASE37.write_text(original_phase37, encoding="utf-8")

        phase37_data = load(PHASE37)
        phase37_data["executionAuthorized"] = True
        save(PHASE37, phase37_data)
        assert_blocked("execution authorization violation is blocked")
        PHASE37.write_text(original_phase37, encoding="utf-8")

        phase37_data = load(PHASE37)
        phase37_data["safety"]["walletUsed"] = True
        save(PHASE37, phase37_data)
        assert_blocked("wallet safety violation is blocked")
        PHASE37.write_text(original_phase37, encoding="utf-8")

        print("\nRESULT: 12/12 PASSED")

    finally:
        PHASE37.write_text(original_phase37, encoding="utf-8")
        BASELINE.write_text(original_baseline, encoding="utf-8")

        for path, content in zip(LAYERS, original_layers):
            path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
