#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/aacp-evidence-chain-health-finality-stability-history-continuity-verify.py"

OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASE53_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-verify.json"
)

HISTORY = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history.json"
)

CHECKPOINT = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-checkpoint.json"
)

OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-verify.json"
)


def run_verifier():
    return subprocess.run(
        ["python", str(SOURCE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def assert_blocked(label):
    result = run_verifier()
    assert result.returncode == 1, (
        f"{label}: expected exit 1, got {result.returncode}\n"
        f"{result.stdout}\n{result.stderr}"
    )
    assert OUTPUT.exists(), f"{label}: output missing"

    data = load_json(OUTPUT)

    assert data["state"] == "BLOCKED", (
        f"{label}: state={data.get('state')}"
    )
    assert data["sourceState"] == "BLOCKED"
    assert data["readiness"]["ready"] is False
    assert data["verification"]["valid"] is False
    assert data["verification"]["checkpoint"] == "INVALID"
    assert data["errorCount"] > 0
    assert data["errors"]

    return data


def restore(backup_dir):
    for src, dst in [
        (backup_dir / "phase53.json", PHASE53_OUTPUT),
        (backup_dir / "history.json", HISTORY),
        (backup_dir / "checkpoint.json", CHECKPOINT),
    ]:
        if src.exists():
            shutil.copy2(src, dst)
        elif dst.exists():
            dst.unlink()


def clean_runtime():
    for p in [CHECKPOINT, OUTPUT]:
        if p.exists():
            p.unlink()


def establish():
    clean_runtime()
    result = run_verifier()
    assert result.returncode == 0
    data = load_json(OUTPUT)
    assert data["state"] == "CHECKPOINT_ESTABLISHED"
    assert data["verification"]["valid"] is True
    assert data["verification"]["verifiedLayers"] == 0
    assert data["verification"]["requiredLayers"] == 1
    return data


def verify():
    result = run_verifier()
    assert result.returncode == 0
    data = load_json(OUTPUT)
    assert data["state"] == "VERIFIED_READ_ONLY"
    assert data["sourceState"] == "VERIFIED_READ_ONLY"
    assert data["readiness"]["ready"] is True
    assert data["verification"]["valid"] is True
    assert data["verification"]["checkpoint"] == "VERIFIED"
    assert data["verification"]["requiredLayers"] == 1
    assert data["verification"]["verifiedLayers"] == 1
    assert data["errorCount"] == 0
    return data


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    assert PHASE53_OUTPUT.exists(), "Phase53 output missing"
    assert HISTORY.exists(), "Phase53 history missing"

    with tempfile.TemporaryDirectory() as td:
        backup = Path(td)

        shutil.copy2(PHASE53_OUTPUT, backup / "phase53.json")
        shutil.copy2(HISTORY, backup / "history.json")

        if CHECKPOINT.exists():
            shutil.copy2(CHECKPOINT, backup / "checkpoint.json")

        tests = []

        # 1. Clean first-run checkpoint establishment.
        establish()
        tests.append("checkpoint establishment")

        # 2. Clean continuity verification.
        verify()
        tests.append("normal continuity verification")

        # Capture deterministic digest.
        baseline = load_json(OUTPUT)
        baseline_digest = baseline["verification"]["continuityDigest"]

        # 3. Second unchanged verification is deterministic.
        verify()
        again = load_json(OUTPUT)
        assert again["verification"]["continuityDigest"] == baseline_digest
        tests.append("deterministic continuity digest")

        # 4. Phase53 generatedAt-only changes are intentionally ignored.
        # Phase54 continuity projection excludes the top-level generatedAt.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["generatedAt"] = "2099-01-01T00:00:00+00:00"
        save_json(PHASE53_OUTPUT, phase53)

        result = run_verifier()
        assert result.returncode == 0, (
            "Phase53 generatedAt-only change: expected exit 0, "
            f"got {result.returncode}\\n{result.stdout}\\n{result.stderr}"
        )

        data = load_json(OUTPUT)
        assert data["state"] == "VERIFIED_READ_ONLY"
        assert data["readiness"]["ready"] is True
        assert data["verification"]["valid"] is True
        assert data["verification"]["checkpoint"] == "VERIFIED"
        assert data["verification"]["continuityDigest"] == baseline_digest
        assert data["errorCount"] == 0

        restore(backup)
        establish()
        verify()
        tests.append("Phase53 generatedAt-only change ignored")

        # 5. Phase53 historyDigest drift.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["verification"]["historyDigest"] = "0" * 64
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("Phase53 historyDigest drift")
        restore(backup)
        establish()
        verify()
        tests.append("Phase53 historyDigest drift blocked")

        # 6. Phase53 stabilityDigest drift.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["verification"]["stabilityDigest"] = "1" * 64
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("Phase53 stabilityDigest drift")
        restore(backup)
        establish()
        verify()
        tests.append("Phase53 stabilityDigest drift blocked")

        # 7. Phase53 readiness drift.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["readiness"]["ready"] = False
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("Phase53 readiness drift")
        restore(backup)
        establish()
        verify()
        tests.append("Phase53 readiness drift blocked")

        # 8. Phase53 validity drift.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["verification"]["valid"] = False
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("Phase53 validity drift")
        restore(backup)
        establish()
        verify()
        tests.append("Phase53 validity drift blocked")

        # 9. Phase53 execution authorization violation.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["executionAuthorized"] = True
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("execution authorization violation")
        restore(backup)
        establish()
        verify()
        tests.append("execution authorization blocked")

        # 10. Wallet safety violation.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["safety"]["walletUsed"] = True
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("wallet safety violation")
        restore(backup)
        establish()
        verify()
        tests.append("wallet safety blocked")

        # 11. Signing safety violation.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["safety"]["signingPerformed"] = True
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("signing safety violation")
        restore(backup)
        establish()
        verify()
        tests.append("signing safety blocked")

        # 12. Broadcast safety violation.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["safety"]["broadcastPerformed"] = True
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("broadcast safety violation")
        restore(backup)
        establish()
        verify()
        tests.append("broadcast safety blocked")

        # 13. Submission safety violation.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["safety"]["submissionPerformed"] = True
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("submission safety violation")
        restore(backup)
        establish()
        verify()
        tests.append("submission safety blocked")

        # 14. Phase53 errorCount violation.
        phase53 = load_json(PHASE53_OUTPUT)
        phase53["errorCount"] = 1
        save_json(PHASE53_OUTPUT, phase53)
        assert_blocked("Phase53 errorCount violation")
        restore(backup)
        establish()
        verify()
        tests.append("Phase53 errorCount blocked")

        # 15. Missing Phase53 output.
        PHASE53_OUTPUT.unlink()
        assert_blocked("missing Phase53 output")
        restore(backup)
        establish()
        verify()
        tests.append("missing Phase53 output blocked")

        # 16. Corrupt Phase53 output.
        PHASE53_OUTPUT.write_text("{broken-json\n", encoding="utf-8")
        assert_blocked("corrupt Phase53 output")
        restore(backup)
        establish()
        verify()
        tests.append("corrupt Phase53 output blocked")

        # 17. Missing history must fail closed.
        HISTORY.unlink()
        assert_blocked("missing history")
        restore(backup)
        establish()
        verify()
        tests.append("missing history blocked")

        # 18. Corrupt history must fail closed.
        HISTORY.write_text("{broken-history\n", encoding="utf-8")
        assert_blocked("corrupt history")
        restore(backup)
        establish()
        verify()
        tests.append("corrupt history blocked")

        # 19. History observation count tampering.
        history = load_json(HISTORY)
        history["observations"] = history["observations"][:2]
        save_json(HISTORY, history)
        assert_blocked("history observation count tampering")
        restore(backup)
        establish()
        verify()
        tests.append("history observation count blocked")

        # 20. History observation digest tampering.
        history = load_json(HISTORY)
        history["observations"][0]["stabilityDigest"] = "2" * 64
        save_json(HISTORY, history)
        assert_blocked("history observation digest tampering")
        restore(backup)
        establish()
        verify()
        tests.append("history observation digest blocked")

        # 21. Checkpoint corruption.
        checkpoint = load_json(CHECKPOINT)
        checkpoint["continuityDigest"] = "3" * 64
        save_json(CHECKPOINT, checkpoint)
        assert_blocked("checkpoint digest tampering")
        restore(backup)
        establish()
        verify()
        tests.append("checkpoint digest tampering blocked")

        # 22. Checkpoint projection tampering.
        checkpoint = load_json(CHECKPOINT)
        checkpoint["checkpointProjection"]["phase53"]["valid"] = False
        save_json(CHECKPOINT, checkpoint)
        assert_blocked("checkpoint projection tampering")
        restore(backup)
        establish()
        verify()
        tests.append("checkpoint projection tampering blocked")

        # 23. Checkpoint type tampering.
        checkpoint = load_json(CHECKPOINT)
        checkpoint["type"] = "WRONG_TYPE"
        save_json(CHECKPOINT, checkpoint)
        assert_blocked("checkpoint type tampering")
        restore(backup)
        establish()
        verify()
        tests.append("checkpoint type tampering blocked")

        # 24. Final restored state must verify.
        restore(backup)
        establish()
        final = verify()
        assert final["verification"]["continuityDigest"] == baseline_digest
        tests.append("restored continuity verification")

        print(f"{len(tests)}/{len(tests)} PASSED")
        for i, name in enumerate(tests, 1):
            print(f"[PASS] {i:02d} {name}")


if __name__ == "__main__":
    main()
