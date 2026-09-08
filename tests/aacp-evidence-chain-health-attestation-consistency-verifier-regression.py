#!/usr/bin/env python3

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/aacp-evidence-chain-health-attestation-consistency-verifier.py"

SOURCE_NAME = (
    "latest-aacp-evidence-chain-health-integrity-attestation.json"
)

OUTPUT_NAME = (
    "latest-aacp-evidence-chain-health-attestation-consistency-verify.json"
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


def digest_payload(p):
    canonical = json.dumps(
        p,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()

    return hashlib.sha256(canonical).hexdigest()


def make_attestation():
    payload = {
        "phase31Sha256": "a" * 64,
        "phase32Sha256": "b" * 64,
        "phase33Sha256": "c" * 64,
    }

    digest = digest_payload(payload)

    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
        "generatedAt": "2026-09-09T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "safety": copy.deepcopy(SAFETY),
        "sideEffects": {
            "network": False,
            "filesystemWrite": True,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "verification": {
            "valid": True,
            "phase31Exists": True,
            "phase32Exists": True,
            "phase33Exists": True,
            "phase31Sha256": payload["phase31Sha256"],
            "phase32Sha256": payload["phase32Sha256"],
            "phase33Sha256": payload["phase33Sha256"],
            "canonicalPayloadSha256": digest,
            "attestationDigest": digest,
        },
        "sources": {
            "phase31": {
                "file": "phase31.json",
                "exists": True,
                "sha256": payload["phase31Sha256"],
                "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
            },
            "phase32": {
                "file": "phase32.json",
                "exists": True,
                "sha256": payload["phase32Sha256"],
                "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
            },
            "phase33": {
                "file": "phase33.json",
                "exists": True,
                "sha256": payload["phase33Sha256"],
                "type": "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
            },
        },
        "errors": [],
        "errorCount": 0,
        "policy": copy.deepcopy(POLICY),
    }


def write_source(tmp, report):
    path = tmp / SOURCE_NAME

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
        )
        f.write("\n")

    return path


def run(tmp):
    env = os.environ.copy()
    env["AACP_OUTPUT_DIR"] = str(tmp)

    return subprocess.run(
        [sys.executable, str(SRC)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def read_output(tmp):
    path = tmp / OUTPUT_NAME

    assert path.exists(), "output JSON missing"

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_valid(tmp):
    return write_source(
        tmp,
        make_attestation(),
    )


def case_valid(tmp):
    make_valid(tmp)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode == 0
    assert r["verification"]["valid"] is True
    assert r["state"] == "VERIFIED_READ_ONLY"
    assert r["sourceState"] == "VERIFIED_READ_ONLY"
    assert r["errorCount"] == 0


def case_missing_source(tmp):
    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert r["verification"]["valid"] is False
    assert r["state"] == "BLOCKED"
    assert r["sourceState"] == "BLOCKED"


def case_invalid_json(tmp):
    path = tmp / SOURCE_NAME
    path.write_text("{invalid", encoding="utf-8")

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert r["verification"]["valid"] is False
    assert any(
        e["code"] == "SOURCE_INVALID_JSON"
        for e in r["errors"]
    )


def case_wrong_type(tmp):
    report = make_attestation()
    report["type"] = "WRONG"

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert r["verification"]["valid"] is False


def case_wrong_mode(tmp):
    report = make_attestation()
    report["mode"] = "WRITE"

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert r["verification"]["valid"] is False


def case_execution_authorized(tmp):
    report = make_attestation()
    report["executionAuthorized"] = True

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert r["verification"]["valid"] is False
    assert any(
        e["code"] == "EXECUTION_AUTHORIZED"
        for e in r["errors"]
    )


def case_safety_violation(tmp):
    report = make_attestation()
    report["safety"]["walletUsed"] = True

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert r["verification"]["valid"] is False
    assert any(
        e["code"] == "SAFETY_INVALID"
        for e in r["errors"]
    )


def case_policy_violation(tmp):
    report = make_attestation()
    report["policy"]["readOnly"] = False

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert r["verification"]["valid"] is False
    assert any(
        e["code"] == "POLICY_INVALID"
        for e in r["errors"]
    )


def case_attestation_invalid(tmp):
    report = make_attestation()
    report["verification"]["valid"] = False

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "ATTESTATION_NOT_VALID"
        for e in r["errors"]
    )


def case_phase31_missing_flag(tmp):
    report = make_attestation()
    report["verification"]["phase31Exists"] = False

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "PHASE31_NOT_PRESENT"
        for e in r["errors"]
    )


def case_phase32_missing_flag(tmp):
    report = make_attestation()
    report["verification"]["phase32Exists"] = False

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "PHASE32_NOT_PRESENT"
        for e in r["errors"]
    )


def case_phase33_missing_flag(tmp):
    report = make_attestation()
    report["verification"]["phase33Exists"] = False

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "PHASE33_NOT_PRESENT"
        for e in r["errors"]
    )


def case_canonical_digest_tamper(tmp):
    report = make_attestation()
    report["verification"]["canonicalPayloadSha256"] = "d" * 64

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "CANONICAL_DIGEST_MISMATCH"
        for e in r["errors"]
    )


def case_attestation_digest_tamper(tmp):
    report = make_attestation()
    report["verification"]["attestationDigest"] = "e" * 64

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "ATTESTATION_DIGEST_MISMATCH"
        for e in r["errors"]
    )


def case_phase_hash_invalid(tmp):
    report = make_attestation()
    report["verification"]["phase31Sha256"] = "bad"

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "SOURCE_HASHES_INVALID"
        for e in r["errors"]
    )


def case_full_report_copy(tmp):
    report = make_attestation()
    report["fullReport"] = {
        "secret": "must-not-be-copied",
    }

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "FULL_REPORT_COPY"
        for e in r["errors"]
    )


def case_source_sha_mismatch(tmp):
    report = make_attestation()
    report["verification"]["sourceSha256"] = "f" * 64

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode != 0
    assert any(
        e["code"] == "SOURCE_SHA_MISMATCH"
        for e in r["errors"]
    )


def case_compact_output(tmp):
    make_valid(tmp)

    p = run(tmp)
    r = read_output(tmp)

    assert p.returncode == 0

    forbidden = {
        "content",
        "report",
        "fullReport",
        "full_report",
        "raw",
        "rawReport",
        "raw_report",
    }

    assert not forbidden.intersection(r.keys())


def case_deterministic_digest(tmp):
    make_valid(tmp)

    p1 = run(tmp)
    r1 = read_output(tmp)

    assert p1.returncode == 0

    digest1 = r1["verification"]["sourceSha256"]

    p2 = run(tmp)
    r2 = read_output(tmp)

    assert p2.returncode == 0

    digest2 = r2["verification"]["sourceSha256"]

    assert digest1 == digest2


def case_error_count(tmp):
    report = make_attestation()
    report["errorCount"] = 99

    write_source(tmp, report)

    p = run(tmp)
    r = read_output(tmp)

    # The Phase 35 verifier intentionally treats Phase 34's
    # errorCount as source metadata; it must not blindly trust
    # it as its own error count.
    assert p.returncode == 0
    assert r["verification"]["valid"] is True
    assert r["errorCount"] == 0


def case_source_safety_scan(tmp):
    text = SRC.read_text(encoding="utf-8")

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

    # subprocess is used by the regression runner, not the verifier.
    # This scan therefore checks the source with an allow-list for the
    # legitimate subprocess-free implementation.
    assert "subprocess" not in text

    for item in forbidden:
        if item == "subprocess":
            continue
        assert item not in text


CASES = [
    ("01 valid chain", case_valid),
    ("02 missing source", case_missing_source),
    ("03 invalid JSON", case_invalid_json),
    ("04 wrong type", case_wrong_type),
    ("05 wrong mode", case_wrong_mode),
    ("06 execution authorized", case_execution_authorized),
    ("07 safety violation", case_safety_violation),
    ("08 policy violation", case_policy_violation),
    ("09 attestation invalid", case_attestation_invalid),
    ("10 Phase31 missing flag", case_phase31_missing_flag),
    ("11 Phase32 missing flag", case_phase32_missing_flag),
    ("12 Phase33 missing flag", case_phase33_missing_flag),
    ("13 canonical digest tamper", case_canonical_digest_tamper),
    ("14 attestation digest tamper", case_attestation_digest_tamper),
    ("15 source hash invalid", case_phase_hash_invalid),
    ("16 full report copy", case_full_report_copy),
    ("17 source SHA mismatch", case_source_sha_mismatch),
    ("18 compact output", case_compact_output),
    ("19 deterministic digest", case_deterministic_digest),
    ("20 error count isolation", case_error_count),
    ("21 source safety scan", case_source_safety_scan),
]


def main():
    for name, case in CASES:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)

            try:
                case(tmp)
                print(f"[PASS] {name}")
            except Exception as exc:
                print(f"[FAIL] {name}: {exc}")
                return 1

    print()
    print(
        f"PHASE 35 REGRESSION: {len(CASES)}/{len(CASES)} PASSED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
