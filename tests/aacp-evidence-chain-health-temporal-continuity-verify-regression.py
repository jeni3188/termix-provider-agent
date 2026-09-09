#!/usr/bin/env python3

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/aacp-evidence-chain-health-temporal-continuity-verify.py"
BASE = ROOT / "provider-output/aacp-observer"

CHECKPOINT = BASE / "aacp-evidence-chain-health-temporal-continuity-checkpoint.json"
OUTPUT = BASE / "latest-aacp-evidence-chain-health-temporal-continuity-verify.json"

PHASE_FILES = {
    31: "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
    32: "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
    33: "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
    34: "latest-aacp-evidence-chain-health-integrity-attestation.json",
    35: "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
    36: "latest-aacp-evidence-chain-health-final-readiness.json",
    37: "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json",
    38: "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json",
    39: "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json",
    40: "latest-aacp-evidence-chain-health-snapshot-registry.json",
    41: "latest-aacp-evidence-chain-health-snapshot-registry-verify.json",
    42: "latest-aacp-evidence-chain-health-snapshot-registry-continuity-verify.json",
}


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def run():
    return subprocess.run(
        [sys.executable, str(SRC)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def assert_true(condition, label):
    if not condition:
        raise AssertionError(label)
    print(f"PASS: {label}")


originals = {}

try:
    BASE.mkdir(parents=True, exist_ok=True)

    for phase, filename in PHASE_FILES.items():
        path = BASE / filename
        originals[phase] = path.read_bytes()

    checkpoint_original = CHECKPOINT.read_bytes() if CHECKPOINT.exists() else None
    output_original = OUTPUT.read_bytes() if OUTPUT.exists() else None

    # 1. Normal continuity
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode == 0
        and data["state"] == "VERIFIED_READ_ONLY"
        and data["verification"]["valid"] is True
        and data["verification"]["verifiedLayers"] == 12,
        "normal temporal continuity verifies 12/12",
    )

    # 2. Missing phase
    p = BASE / PHASE_FILES[31]
    p.unlink()
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0
        and data["state"] == "BLOCKED"
        and data["verification"]["valid"] is False,
        "missing phase artifact is blocked",
    )
    p.write_bytes(originals[31])

    # 3. Corrupted JSON
    p = BASE / PHASE_FILES[32]
    p.write_text("{corrupted")
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "corrupted JSON is blocked",
    )
    p.write_bytes(originals[32])

    # 4. Wrong type
    p = BASE / PHASE_FILES[33]
    mutated = load(p)
    mutated["type"] = "WRONG_TYPE"
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "wrong artifact type is blocked",
    )
    p.write_bytes(originals[33])

    # 5. Phase42 readiness violation
    p = BASE / PHASE_FILES[42]
    mutated = load(p)
    mutated["readiness"]["ready"] = False
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "phase42 readiness violation is blocked",
    )
    p.write_bytes(originals[42])

    # 6. Phase42 validity violation
    p = BASE / PHASE_FILES[42]
    mutated = load(p)
    mutated["verification"]["valid"] = False
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "phase42 validity violation is blocked",
    )
    p.write_bytes(originals[42])

    # 7. Execution authorization
    p = BASE / PHASE_FILES[36]
    mutated = load(p)
    mutated["executionAuthorized"] = True
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "execution authorization violation is blocked",
    )
    p.write_bytes(originals[36])

    # 8. Wallet safety
    p = BASE / PHASE_FILES[37]
    mutated = load(p)
    mutated["safety"]["walletUsed"] = True
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "wallet safety violation is blocked",
    )
    p.write_bytes(originals[37])

    # 9. Signing safety
    p = BASE / PHASE_FILES[38]
    mutated = load(p)
    mutated["safety"]["signingPerformed"] = True
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "signing safety violation is blocked",
    )
    p.write_bytes(originals[38])

    # 10. Broadcast safety
    p = BASE / PHASE_FILES[39]
    mutated = load(p)
    mutated["safety"]["broadcastPerformed"] = True
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "broadcast safety violation is blocked",
    )
    p.write_bytes(originals[39])

    # 11. Submission safety
    p = BASE / PHASE_FILES[40]
    mutated = load(p)
    mutated["safety"]["submissionPerformed"] = True
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "submission safety violation is blocked",
    )
    p.write_bytes(originals[40])

    # 12. Error count
    p = BASE / PHASE_FILES[41]
    mutated = load(p)
    mutated["errorCount"] = 1
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "nonzero error count is blocked",
    )
    p.write_bytes(originals[41])

    # 13. Timestamp regression
    p = BASE / PHASE_FILES[42]
    mutated = load(p)

    phase41 = load(BASE / PHASE_FILES[41])
    mutated["generatedAt"] = phase41["generatedAt"]

    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "timestamp regression is blocked",
    )
    p.write_bytes(originals[42])

    # 14. Malformed timestamp
    p = BASE / PHASE_FILES[42]
    mutated = load(p)
    mutated["generatedAt"] = "not-a-timestamp"
    save(p, mutated)
    result = run()
    data = load(OUTPUT)
    assert_true(
        result.returncode != 0 and data["state"] == "BLOCKED",
        "malformed timestamp is blocked",
    )
    p.write_bytes(originals[42])

    # 15. Deterministic semantic digest
    result1 = run()
    data1 = load(OUTPUT)

    result2 = run()
    data2 = load(OUTPUT)

    assert_true(
        result1.returncode == 0
        and result2.returncode == 0
        and data1["verification"]["semanticDigest"]
        == data2["verification"]["semanticDigest"],
        "semantic digest is deterministic",
    )

    print("RESULT: 15/15 PASSED")

finally:
    for phase, content in originals.items():
        (BASE / PHASE_FILES[phase]).write_bytes(content)

    if checkpoint_original is None:
        CHECKPOINT.unlink(missing_ok=True)
    else:
        CHECKPOINT.write_bytes(checkpoint_original)

    if output_original is None:
        OUTPUT.unlink(missing_ok=True)
    else:
        OUTPUT.write_bytes(output_original)

    for cache in (
        ROOT / "src" / "__pycache__",
        ROOT / "tests" / "__pycache__",
    ):
        if cache.exists():
            import shutil
            shutil.rmtree(cache)
