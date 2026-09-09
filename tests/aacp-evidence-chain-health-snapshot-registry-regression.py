#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OBSERVER_DIR = BASE_DIR / "provider-output" / "aacp-observer"

SOURCE = BASE_DIR / "src" / "aacp-evidence-chain-health-snapshot-registry.py"
OUTPUT = OBSERVER_DIR / "latest-aacp-evidence-chain-health-snapshot-registry.json"

PHASE_FILES = {
    31: OBSERVER_DIR / "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
    32: OBSERVER_DIR / "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
    33: OBSERVER_DIR / "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
    34: OBSERVER_DIR / "latest-aacp-evidence-chain-health-integrity-attestation.json",
    35: OBSERVER_DIR / "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
    36: OBSERVER_DIR / "latest-aacp-evidence-chain-health-final-readiness.json",
    37: OBSERVER_DIR / "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json",
    38: OBSERVER_DIR / "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json",
    39: OBSERVER_DIR / "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json",
}


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


def expect(label, condition):
    if not condition:
        raise AssertionError(label)
    print(f"PASS: {label}")


def main():
    original = {
        p: p.read_text(encoding="utf-8")
        for p in PHASE_FILES.values()
    }

    try:
        # 1. Normal registry
        result = run()
        data = load(OUTPUT)
        expect(
            "normal registry verifies 9/9",
            result.returncode == 0
            and data["state"] == "VERIFIED_READ_ONLY"
            and data["verification"]["valid"] is True
            and data["verification"]["verifiedLayers"] == 9,
        )

        # 2. Missing Phase31
        p = PHASE_FILES[31]
        backup = p.read_text(encoding="utf-8")
        p.unlink()
        result = run()
        data = load(OUTPUT)
        expect(
            "missing phase31 is blocked",
            result.returncode == 1
            and data["state"] == "BLOCKED"
            and data["verification"]["valid"] is False,
        )
        p.write_text(backup, encoding="utf-8")

        # 3. Missing Phase39
        p = PHASE_FILES[39]
        backup = p.read_text(encoding="utf-8")
        p.unlink()
        result = run()
        data = load(OUTPUT)
        expect(
            "missing phase39 is blocked",
            result.returncode == 1
            and data["state"] == "BLOCKED",
            )
        p.write_text(backup, encoding="utf-8")

        # 4. Corrupted JSON
        p = PHASE_FILES[36]
        backup = p.read_text(encoding="utf-8")
        p.write_text("{broken-json\n", encoding="utf-8")
        result = run()
        data = load(OUTPUT)
        expect(
            "corrupted phase36 JSON is blocked",
            result.returncode == 1
            and data["state"] == "BLOCKED",
        )
        p.write_text(backup, encoding="utf-8")

        # 5. Wrong type
        p = PHASE_FILES[35]
        data0 = load(p)
        data0["type"] = "WRONG_TYPE"
        save(p, data0)
        result = run()
        data = load(OUTPUT)
        expect(
            "wrong phase35 type is blocked",
            result.returncode == 1
            and data["state"] == "BLOCKED",
        )
        p.write_text(original[p], encoding="utf-8")

        # 6. Execution authorization violation
        p = PHASE_FILES[39]
        data0 = load(p)
        data0["executionAuthorized"] = True
        save(p, data0)
        result = run()
        data = load(OUTPUT)
        expect(
            "execution authorization violation is blocked",
            result.returncode == 1
            and data["state"] == "BLOCKED",
        )
        p.write_text(original[p], encoding="utf-8")

        # 7. Wallet safety violation
        p = PHASE_FILES[38]
        data0 = load(p)
        data0["safety"]["walletUsed"] = True
        save(p, data0)
        result = run()
        data = load(OUTPUT)
        expect(
            "wallet safety violation is blocked",
            result.returncode == 1
            and data["state"] == "BLOCKED",
        )
        p.write_text(original[p], encoding="utf-8")

        # 8. Error count violation
        p = PHASE_FILES[37]
        data0 = load(p)
        data0["errorCount"] = 1
        save(p, data0)
        result = run()
        data = load(OUTPUT)
        expect(
            "nonzero error count is blocked",
            result.returncode == 1
            and data["state"] == "BLOCKED",
        )
        p.write_text(original[p], encoding="utf-8")

        # 9. Phase31 incomplete state remains valid
        p = PHASE_FILES[31]
        data0 = load(p)
        expect(
            "phase31 incomplete semantic state is accepted",
            data0["state"] == "INCOMPLETE"
            and data0["executionAuthorized"] is False
            and data0["errorCount"] == 0,
        )

        result = run()
        data = load(OUTPUT)
        expect(
            "phase31 incomplete state does not block registry",
            result.returncode == 0
            and data["verification"]["verifiedLayers"] == 9,
        )

        # 10. Phase32 incomplete verifier state remains valid
        p = PHASE_FILES[32]
        data0 = load(p)
        expect(
            "phase32 incomplete verifier state is accepted",
            data0["state"] == "INCOMPLETE"
            and data0["verification"]["valid"] is True
            and data0["executionAuthorized"] is False,
        )

        result = run()
        data = load(OUTPUT)
        expect(
            "phase32 incomplete state does not block registry",
            result.returncode == 0
            and data["verification"]["verifiedLayers"] == 9,
        )

        # 11. Deterministic registry digest
        result1 = run()
        digest1 = load(OUTPUT)["registry"]["registryDigest"]

        result2 = run()
        digest2 = load(OUTPUT)["registry"]["registryDigest"]

        expect(
            "registry digest is deterministic",
            result1.returncode == 0
            and result2.returncode == 0
            and digest1 == digest2
            and len(digest1) == 64,
        )

        print("\nRESULT: 13/13 PASSED")

    finally:
        for p, content in original.items():
            p.write_text(content, encoding="utf-8")

        # Restore final live artifact
        run()


if __name__ == "__main__":
    main()
