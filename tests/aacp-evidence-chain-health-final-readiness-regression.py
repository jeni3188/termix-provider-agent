#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/aacp-evidence-chain-health-final-readiness.py"

PHASES = [
    "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
    "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
    "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
    "latest-aacp-evidence-chain-health-integrity-attestation.json",
    "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
]


def run(tmp):
    env = os.environ.copy()
    env["AACP_OUTPUT_DIR"] = str(tmp)

    return subprocess.run(
        [sys.executable, str(SOURCE)],
        env=env,
        capture_output=True,
        text=True,
    )


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def base_report(index):
    types = [
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
        "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
        "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
        "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
    ]

    return {
        "version": "1.0.0",
        "type": types[index],
        "generatedAt": "2026-09-09T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "safety": {
            "postPerformed": False,
            "walletUsed": False,
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
        },
        "verification": {
            "valid": True,
            "sourceExists": True,
            "sourceSha256": "a" * 64,
            "sha256": "a" * 64,
            "phase31Sha256": "a" * 64,
            "phase32Sha256": "b" * 64,
            "phase33Sha256": "c" * 64,
        },
        "errors": [],
        "errorCount": 0,
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "post": "NOT_PERFORMED",
            "wallet": "NOT_USED",
            "signing": "NOT_PERFORMED",
            "broadcast": "NOT_PERFORMED",
            "submission": "NOT_PERFORMED",
        },
    }


def make_chain(tmp):
    for i, name in enumerate(PHASES):
        write(tmp / name, base_report(i))


def load_output(tmp):
    return json.loads(
        (tmp / "latest-aacp-evidence-chain-health-final-readiness.json")
        .read_text()
    )


def test_valid():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        p = run(tmp)

        # Synthetic hashes intentionally do not match actual files.
        assert p.returncode != 0

        out = load_output(tmp)
        assert out["state"] == "BLOCKED"
        assert out["readiness"]["ready"] is False


def test_missing():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)
        (tmp / PHASES[2]).unlink()

        p = run(tmp)
        assert p.returncode != 0

        out = load_output(tmp)
        assert out["state"] == "BLOCKED"
        assert out["readiness"]["ready"] is False


def test_execution_authorized():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[4]).read_text())
        data["executionAuthorized"] = True
        write(tmp / PHASES[4], data)

        p = run(tmp)
        assert p.returncode != 0


def test_safety():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[4]).read_text())
        data["safety"]["walletUsed"] = True
        write(tmp / PHASES[4], data)

        p = run(tmp)
        assert p.returncode != 0


def test_policy():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[4]).read_text())
        data["policy"]["readOnly"] = False
        write(tmp / PHASES[4], data)

        p = run(tmp)
        assert p.returncode != 0


def test_invalid_json():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        (tmp / PHASES[3]).write_text("{broken\n")

        p = run(tmp)
        assert p.returncode != 0


def test_wrong_type():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[1]).read_text())
        data["type"] = "WRONG"
        write(tmp / PHASES[1], data)

        p = run(tmp)
        assert p.returncode != 0


def test_blocked_state():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[0]).read_text())
        data["state"] = "BLOCKED"
        write(tmp / PHASES[0], data)

        p = run(tmp)
        assert p.returncode != 0


def test_error_count():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[4]).read_text())
        data["errorCount"] = 7
        write(tmp / PHASES[4], data)

        p = run(tmp)
        assert p.returncode != 0


def test_full_report_copy():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[4]).read_text())
        data["fullReport"] = {"secret": "copy"}
        write(tmp / PHASES[4], data)

        p = run(tmp)
        assert p.returncode != 0


def test_output_safety():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        run(tmp)
        out = load_output(tmp)

        assert out["executionAuthorized"] is False
        assert out["safety"]["walletUsed"] is False
        assert out["safety"]["signingPerformed"] is False
        assert out["safety"]["broadcastPerformed"] is False
        assert out["safety"]["submissionPerformed"] is False


def test_output_policy():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        run(tmp)
        out = load_output(tmp)

        assert out["policy"]["readOnly"] is True
        assert out["policy"]["failClosed"] is True
        assert out["policy"]["post"] == "NOT_PERFORMED"
        assert out["policy"]["wallet"] == "NOT_USED"
        assert out["policy"]["signing"] == "NOT_PERFORMED"
        assert out["policy"]["broadcast"] == "NOT_PERFORMED"
        assert out["policy"]["submission"] == "NOT_PERFORMED"


def test_compact_output():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        run(tmp)
        out = load_output(tmp)

        assert set(out.keys()) == {
            "version",
            "type",
            "generatedAt",
            "mode",
            "state",
            "sourceState",
            "executionAuthorized",
            "safety",
            "sideEffects",
            "readiness",
            "verification",
            "sources",
            "errors",
            "errorCount",
            "policy",
        }


def test_no_runtime_primitives():
    text = SOURCE.read_text(encoding="utf-8")

    forbidden = [
        "requests",
        "urllib",
        "httpx",
        "aiohttp",
        "websocket",
        "socket",
        "subprocess",
        "os.system",
        "Popen",
        "check_call",
        "check_output",
        "sendTransaction",
        "sendRawTransaction",
    ]

    for item in forbidden:
        assert item not in text, item


def test_no_wallet_execution():
    text = SOURCE.read_text(encoding="utf-8")

    forbidden = [
        "private_key",
        "PRIVATE_KEY",
        "mnemonic",
        "sign_transaction",
        "signTransaction",
        "broadcastTransaction",
    ]

    for item in forbidden:
        assert item not in text, item


def test_fail_closed_exit():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)

        p = run(tmp)

        assert p.returncode != 0
        assert (tmp / "latest-aacp-evidence-chain-health-final-readiness.json").exists()

        out = load_output(tmp)
        assert out["state"] == "BLOCKED"
        assert out["readiness"]["ready"] is False


def test_side_effect_metadata():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        run(tmp)
        out = load_output(tmp)

        assert out["sideEffects"]["network"] is False
        assert out["sideEffects"]["filesystemWrite"] is True
        assert out["sideEffects"]["wallet"] is False
        assert out["sideEffects"]["signing"] is False
        assert out["sideEffects"]["broadcast"] is False
        assert out["sideEffects"]["submission"] is False


def test_layer_count():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        run(tmp)
        out = load_output(tmp)

        assert out["verification"]["requiredLayers"] == 5


def test_allowed_states():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        run(tmp)
        out = load_output(tmp)

        assert out["state"] in {
            "INCOMPLETE",
            "BLOCKED",
            "VERIFIED_READ_ONLY",
        }


def test_output_never_ready_when_dependency_invalid():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        data = json.loads((tmp / PHASES[0]).read_text())
        data["verification"]["valid"] = False
        write(tmp / PHASES[0], data)

        p = run(tmp)
        out = load_output(tmp)

        assert p.returncode != 0
        assert out["readiness"]["ready"] is False
        assert out["state"] == "BLOCKED"


def test_source_sha_present():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        make_chain(tmp)

        run(tmp)
        out = load_output(tmp)

        for name in PHASES:
            # Every source entry must expose deterministic metadata.
            source_key = next(
                key for key in out["sources"]
                if out["sources"][key]["file"].endswith(name)
            )
            assert len(out["sources"][source_key]["sha256"]) == 64


def main():
    tests = [
        test_valid,
        test_missing,
        test_execution_authorized,
        test_safety,
        test_policy,
        test_invalid_json,
        test_wrong_type,
        test_blocked_state,
        test_error_count,
        test_full_report_copy,
        test_output_safety,
        test_output_policy,
        test_compact_output,
        test_no_runtime_primitives,
        test_no_wallet_execution,
        test_fail_closed_exit,
        test_side_effect_metadata,
        test_layer_count,
        test_allowed_states,
        test_output_never_ready_when_dependency_invalid,
        test_source_sha_present,
    ]

    passed = 0

    for i, test in enumerate(tests, 1):
        try:
            test()
            print(f"[PASS] {i:02d} {test.__name__}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {i:02d} {test.__name__}: {exc}")

    print()
    print(f"PHASE 36 REGRESSION: {passed}/{len(tests)} PASSED")

    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
