#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/aacp-evidence-chain-health-integrity-attestation.py"

PHASE31_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-history.json"
)
PHASE32_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json"
)
PHASE33_NAME = (
    "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json"
)
OUTPUT_NAME = (
    "latest-aacp-evidence-chain-health-integrity-attestation.json"
)


SAFETY = {
    "postPerformed": False,
    "walletUsed": False,
    "signingPerformed": False,
    "broadcastPerformed": False,
    "submissionPerformed": False,
}

POLICY = {
    "readOnly": True,
    "failClosed": True,
    "post": "NOT_PERFORMED",
    "wallet": "NOT_USED",
    "signing": "NOT_PERFORMED",
    "broadcast": "NOT_PERFORMED",
    "submission": "NOT_PERFORMED",
}


def run(tmp):
    env = os.environ.copy()
    env["AACP_OUTPUT_DIR"] = str(tmp)

    return subprocess.run(
        ["python", str(SRC)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def load_output(tmp):
    p = tmp / OUTPUT_NAME
    assert p.exists(), "output missing"
    return json.loads(p.read_text())


def write_json(tmp, name, value):
    (tmp / name).write_text(
        json.dumps(value, indent=2) + "\n"
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_phase31(state="INCOMPLETE"):
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": state,
        "executionAuthorized": False,
        "safety": dict(SAFETY),
        "sideEffects": {
            "post": False,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def base_phase32(phase31_sha, state="INCOMPLETE"):
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": state,
        "executionAuthorized": False,
        "safety": dict(SAFETY),
        "sideEffects": {
            "post": False,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "verification": {
            "valid": True,
            "sourceExists": True,
            "sha256": phase31_sha,
        },
        "sources": {
            "auditHistory": {
                "file": PHASE31_NAME,
                "exists": True,
                "sha256": phase31_sha,
            }
        },
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def base_phase33(phase31_sha, phase32_sha):
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "safety": dict(SAFETY),
        "sideEffects": {
            "post": False,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "verification": {
            "valid": True,
            "phase31Exists": True,
            "phase31Sha256": phase31_sha,
            "phase32Exists": True,
            "phase32Sha256": phase32_sha,
        },
        "sources": {
            "phase31": {
                "file": PHASE31_NAME,
                "exists": True,
                "sha256": phase31_sha,
                "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
            },
            "phase32": {
                "file": PHASE32_NAME,
                "exists": True,
                "sha256": phase32_sha,
                "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
            },
        },
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def make_chain(tmp):
    p31 = base_phase31()
    write_json(tmp, PHASE31_NAME, p31)

    p31_sha = sha256(tmp / PHASE31_NAME)

    p32 = base_phase32(p31_sha)
    write_json(tmp, PHASE32_NAME, p32)

    p32_sha = sha256(tmp / PHASE32_NAME)

    p33 = base_phase33(p31_sha, p32_sha)
    write_json(tmp, PHASE33_NAME, p33)


def assert_safe(r):
    assert r["mode"] == "READ_ONLY"
    assert r["executionAuthorized"] is False
    assert r["safety"] == SAFETY
    assert r["policy"] == POLICY


def case_valid(tmp):
    make_chain(tmp)

    p = run(tmp)
    assert p.returncode == 0, p.stderr

    r = load_output(tmp)

    assert r["state"] == "VERIFIED_READ_ONLY"
    assert r["sourceState"] == "VERIFIED_READ_ONLY"
    assert r["verification"]["valid"] is True
    assert r["errorCount"] == 0
    assert r["verification"]["attestationDigest"]
    assert len(r["verification"]["attestationDigest"]) == 64

    assert_safe(r)


def case_phase32_incomplete_valid(tmp):
    make_chain(tmp)

    p = run(tmp)
    assert p.returncode == 0

    r = load_output(tmp)

    # Critical semantic invariant:
    # Phase 32 may be INCOMPLETE while still valid.
    assert r["state"] == "VERIFIED_READ_ONLY"
    assert r["sourceState"] == "VERIFIED_READ_ONLY"
    assert r["verification"]["valid"] is True


def case_phase33_missing(tmp):
    make_chain(tmp)
    (tmp / PHASE33_NAME).unlink()

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"
    assert r["verification"]["valid"] is False
    assert r["errorCount"] > 0


def case_phase32_missing(tmp):
    make_chain(tmp)
    (tmp / PHASE32_NAME).unlink()

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"
    assert r["verification"]["valid"] is False


def case_phase31_missing(tmp):
    make_chain(tmp)
    (tmp / PHASE31_NAME).unlink()

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"
    assert r["verification"]["valid"] is False


def case_phase33_tamper(tmp):
    make_chain(tmp)

    p33 = tmp / PHASE33_NAME
    x = json.loads(p33.read_text())
    x["verification"]["phase31Sha256"] = "0" * 64
    write_json(tmp, PHASE33_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"
    assert r["verification"]["valid"] is False


def case_phase31_tamper(tmp):
    make_chain(tmp)

    p31 = tmp / PHASE31_NAME
    x = json.loads(p31.read_text())
    x["state"] = "VERIFIED_READ_ONLY"
    write_json(tmp, PHASE31_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"


def case_phase32_sha_mismatch(tmp):
    make_chain(tmp)

    p32 = tmp / PHASE32_NAME
    x = json.loads(p32.read_text())
    x["verification"]["sha256"] = "0" * 64
    write_json(tmp, PHASE32_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"


def case_execution_authorized(tmp):
    make_chain(tmp)

    p32 = tmp / PHASE32_NAME
    x = json.loads(p32.read_text())
    x["executionAuthorized"] = True
    write_json(tmp, PHASE32_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"


def case_safety_violation(tmp):
    make_chain(tmp)

    p33 = tmp / PHASE33_NAME
    x = json.loads(p33.read_text())
    x["safety"]["walletUsed"] = True
    write_json(tmp, PHASE33_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"


def case_policy_violation(tmp):
    make_chain(tmp)

    p33 = tmp / PHASE33_NAME
    x = json.loads(p33.read_text())
    x["policy"]["readOnly"] = False
    write_json(tmp, PHASE33_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"


def case_error_count_mismatch(tmp):
    make_chain(tmp)

    p33 = tmp / PHASE33_NAME
    x = json.loads(p33.read_text())
    x["errorCount"] = 1
    write_json(tmp, PHASE33_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"


def case_invalid_json(tmp):
    make_chain(tmp)

    (tmp / PHASE33_NAME).write_text("{invalid-json")

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"
    assert r["verification"]["valid"] is False


def case_full_report_copy(tmp):
    make_chain(tmp)

    p33 = tmp / PHASE33_NAME
    x = json.loads(p33.read_text())
    x["fullReport"] = {
        "sensitive": "should-not-be-copied"
    }
    write_json(tmp, PHASE33_NAME, x)

    p = run(tmp)
    assert p.returncode != 0

    r = load_output(tmp)

    assert r["state"] == "BLOCKED"


def case_output_safety(tmp):
    make_chain(tmp)

    p = run(tmp)
    assert p.returncode == 0

    r = load_output(tmp)

    assert r["safety"] == SAFETY
    assert r["sideEffects"] == {
        "post": False,
        "wallet": False,
        "signing": False,
        "broadcast": False,
        "submission": False,
    }


def case_compact_metadata(tmp):
    make_chain(tmp)

    p = run(tmp)
    assert p.returncode == 0

    r = load_output(tmp)

    forbidden = {
        "content",
        "report",
        "fullReport",
        "full_report",
        "raw",
        "rawReport",
        "raw_report",
    }

    assert forbidden.isdisjoint(r.keys())


def case_deterministic_digest(tmp):
    make_chain(tmp)

    p = run(tmp)
    assert p.returncode == 0
    r1 = load_output(tmp)

    digest1 = r1["verification"]["attestationDigest"]
    canonical1 = r1["verification"]["canonicalPayloadSha256"]

    # Re-run without modifying source files.
    p = run(tmp)
    assert p.returncode == 0
    r2 = load_output(tmp)

    assert digest1 == r2["verification"]["attestationDigest"]
    assert canonical1 == r2["verification"]["canonicalPayloadSha256"]


def case_source_safety_scan():
    text = SRC.read_text()

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

    for term in forbidden:
        assert term not in text, term


def main():
    cases = [
        ("01 valid chain", case_valid),
        ("02 Phase32 incomplete but valid", case_phase32_incomplete_valid),
        ("03 Phase33 missing", case_phase33_missing),
        ("04 Phase32 missing", case_phase32_missing),
        ("05 Phase31 missing", case_phase31_missing),
        ("06 Phase33 tamper", case_phase33_tamper),
        ("07 Phase31 tamper", case_phase31_tamper),
        ("08 Phase32 SHA mismatch", case_phase32_sha_mismatch),
        ("09 execution authorized", case_execution_authorized),
        ("10 safety violation", case_safety_violation),
        ("11 policy violation", case_policy_violation),
        ("12 error count mismatch", case_error_count_mismatch),
        ("13 invalid JSON", case_invalid_json),
        ("14 full report copy", case_full_report_copy),
        ("15 output safety", case_output_safety),
        ("16 compact metadata", case_compact_metadata),
        ("17 deterministic digest", case_deterministic_digest),
    ]

    passed = 0

    for name, fn in cases:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)

            try:
                fn(tmp)
                print(f"[PASS] {name}")
                passed += 1
            except Exception as exc:
                print(f"[FAIL] {name}: {exc}")
                raise

    case_source_safety_scan()
    print("[PASS] 18 source safety scan")
    passed += 1

    print()
    print(f"PHASE 34 REGRESSION: {passed}/18 PASSED")


if __name__ == "__main__":
    main()
