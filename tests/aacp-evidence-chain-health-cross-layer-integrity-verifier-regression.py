#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "aacp-evidence-chain-health-cross-layer-integrity-verifier.py"
)

PHASE31_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-history.json"
)

PHASE32_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json"
)

AUDIT_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit.json"
)

VERIFY_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-verify.json"
)

OUTPUT_NAME = (
    "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json"
)

PHASE31_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY"
)

PHASE32_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY"
)

PHASE33_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY"
)

SAFE = {
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


def write(path, obj):
    path.write_text(
        json.dumps(obj, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base():
    return {
        "version": "1.0.0",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(SAFE),
        "sideEffects": dict(SAFE),
        "policy": dict(POLICY),
        "errors": [],
        "errorCount": 0,
    }


def make_audit(tmp):
    obj = base()
    obj.update({
        "type": (
            "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT"
        ),
        "generatedAt": "2026-01-01T00:00:00Z",
    })

    write(tmp / AUDIT_NAME, obj)


def make_verify(tmp):
    obj = base()
    obj.update({
        "type": (
            "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_VERIFY"
        ),
        "generatedAt": "2026-01-01T00:00:01Z",
    })

    write(tmp / VERIFY_NAME, obj)


def make_phase31(tmp):
    make_audit(tmp)
    make_verify(tmp)

    audit_path = tmp / AUDIT_NAME
    verify_path = tmp / VERIFY_NAME

    obj = base()
    obj.update({
        "type": PHASE31_TYPE,
        "generatedAt": "2026-01-01T00:00:02Z",
        "snapshots": {
            "audit": {
                "file": AUDIT_NAME,
                "exists": True,
                "sha256": sha(audit_path),
                "state": "INCOMPLETE",
                "sourceState": "INCOMPLETE",
                "executionAuthorized": False,
                "errorCount": 0,
            },
            "verify": {
                "file": VERIFY_NAME,
                "exists": True,
                "sha256": sha(verify_path),
                "state": "INCOMPLETE",
                "sourceState": "INCOMPLETE",
                "executionAuthorized": False,
                "errorCount": 0,
            },
        },
        "consistency": {
            "auditExists": True,
            "verifyExists": True,
            "stateMatch": True,
            "sourceStateMatch": True,
        },
    })

    write(tmp / PHASE31_NAME, obj)


def make_phase32(tmp):
    phase31_path = tmp / PHASE31_NAME

    obj = base()
    obj.update({
        "type": PHASE32_TYPE,
        "generatedAt": "2026-01-01T00:00:03Z",
        "verification": {
            "valid": True,
            "sourceExists": True,
            "sha256": sha(phase31_path),
        },
        "sources": {
            "auditHistory": {
                "file": PHASE31_NAME,
                "exists": True,
                "sha256": sha(phase31_path),
            },
        },
    })

    write(tmp / PHASE32_NAME, obj)


def make_chain(tmp):
    make_phase31(tmp)
    make_phase32(tmp)


def run(tmp):
    env = dict(os.environ)
    env["AACP_OUTPUT_DIR"] = str(tmp)

    return subprocess.run(
        [sys.executable, str(SOURCE)],
        env=env,
        capture_output=True,
        text=True,
    )


def report(tmp):
    return json.loads(
        (tmp / OUTPUT_NAME).read_text(
            encoding="utf-8"
        )
    )


def verified_chain(tmp):
    phase31_path = tmp / PHASE31_NAME

    phase31 = json.loads(
        phase31_path.read_text(encoding="utf-8")
    )

    audit_path = tmp / AUDIT_NAME
    verify_path = tmp / VERIFY_NAME

    for path in (audit_path, verify_path):
        obj = json.loads(
            path.read_text(encoding="utf-8")
        )
        obj["state"] = "VERIFIED_READ_ONLY"
        obj["sourceState"] = "VERIFIED_READ_ONLY"
        write(path, obj)

    phase31["state"] = "VERIFIED_READ_ONLY"
    phase31["sourceState"] = "VERIFIED_READ_ONLY"

    for key, path in (
        ("audit", audit_path),
        ("verify", verify_path),
    ):
        phase31["snapshots"][key]["sha256"] = sha(path)
        phase31["snapshots"][key]["state"] = (
            "VERIFIED_READ_ONLY"
        )
        phase31["snapshots"][key]["sourceState"] = (
            "VERIFIED_READ_ONLY"
        )

    phase31["consistency"] = {
        "auditExists": True,
        "verifyExists": True,
        "stateMatch": True,
        "sourceStateMatch": True,
    }

    write(phase31_path, phase31)
    make_phase32(tmp)

    phase32_path = tmp / PHASE32_NAME
    phase32 = json.loads(
        phase32_path.read_text(encoding="utf-8")
    )

    phase32["state"] = "VERIFIED_READ_ONLY"
    phase32["sourceState"] = "VERIFIED_READ_ONLY"
    phase32["verification"]["valid"] = True
    phase32["verification"]["sha256"] = sha(
        phase31_path
    )
    phase32["sources"]["auditHistory"]["sha256"] = (
        sha(phase31_path)
    )

    write(phase32_path, phase32)


def case_incomplete(tmp):
    make_chain(tmp)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["type"] == PHASE33_TYPE
    assert r["state"] == "VERIFIED_READ_ONLY"
    assert r["sourceState"] == "VERIFIED_READ_ONLY"
    assert r["verification"]["valid"] is True


def case_verified(tmp):
    make_chain(tmp)
    verified_chain(tmp)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["state"] == "VERIFIED_READ_ONLY"
    assert r["sourceState"] == "VERIFIED_READ_ONLY"
    assert r["verification"]["valid"] is True


def case_phase31_missing(tmp):
    make_chain(tmp)
    (tmp / PHASE31_NAME).unlink()

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert r["verification"]["valid"] is False


def case_phase32_missing(tmp):
    make_chain(tmp)
    (tmp / PHASE32_NAME).unlink()

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_phase31_tamper(tmp):
    make_chain(tmp)

    path = tmp / PHASE31_NAME
    obj = json.loads(path.read_text())
    obj["state"] = "VERIFIED_READ_ONLY"
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_phase32_source_sha_tamper(tmp):
    make_chain(tmp)

    path = tmp / PHASE32_NAME
    obj = json.loads(path.read_text())
    obj["sources"]["auditHistory"]["sha256"] = (
        "0" * 64
    )
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_phase32_verification_sha_tamper(tmp):
    make_chain(tmp)

    path = tmp / PHASE32_NAME
    obj = json.loads(path.read_text())
    obj["verification"]["sha256"] = "0" * 64
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_phase32_invalid_json(tmp):
    make_chain(tmp)

    (tmp / PHASE32_NAME).write_text(
        "{invalid\n",
        encoding="utf-8",
    )

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_execution_authorized(tmp):
    make_chain(tmp)

    path = tmp / PHASE31_NAME
    obj = json.loads(path.read_text())
    obj["executionAuthorized"] = True
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_safety_violation(tmp):
    make_chain(tmp)

    path = tmp / PHASE32_NAME
    obj = json.loads(path.read_text())
    obj["safety"]["walletUsed"] = True
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_policy_violation(tmp):
    make_chain(tmp)

    path = tmp / PHASE32_NAME
    obj = json.loads(path.read_text())
    obj["policy"]["readOnly"] = False
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_error_count_mismatch(tmp):
    make_chain(tmp)

    path = tmp / PHASE32_NAME
    obj = json.loads(path.read_text())
    obj["errors"] = [{"code": "X", "message": "x"}]
    obj["errorCount"] = 0
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_full_report_copy(tmp):
    make_chain(tmp)

    path = tmp / PHASE32_NAME
    obj = json.loads(path.read_text())
    obj["fullReport"] = {
        "secret": "forbidden"
    }
    write(path, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_output_safety(tmp):
    make_chain(tmp)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["executionAuthorized"] is False
    assert r["safety"] == SAFE
    assert r["sideEffects"] == SAFE


def case_output_policy(tmp):
    make_chain(tmp)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["policy"] == POLICY


def case_compact_metadata(tmp):
    make_chain(tmp)

    p = run(tmp)
    r = report(tmp)

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

    assert forbidden.isdisjoint(r.keys())
    assert "phase31Sha256" in r["verification"]
    assert "phase32Sha256" in r["verification"]


def case_source_safety_scan(tmp):
    text = SOURCE.read_text(encoding="utf-8")

    forbidden = [
        "requests.",
        "urllib.",
        "httpx",
        "aiohttp",
        "websocket",
        "socket.",
        "subprocess",
        "os.system",
        "os.popen",
        "exec(",
        "eval(",
    ]

    assert not any(item in text for item in forbidden)


CASES = [
    ("01 safe incomplete", case_incomplete),
    ("02 safe verified", case_verified),
    ("03 Phase 31 missing", case_phase31_missing),
    ("04 Phase 32 missing", case_phase32_missing),
    ("05 Phase 31 tamper", case_phase31_tamper),
    ("06 Phase 32 source SHA tamper", case_phase32_source_sha_tamper),
    ("07 Phase 32 verification SHA tamper", case_phase32_verification_sha_tamper),
    ("08 Phase 32 invalid JSON", case_phase32_invalid_json),
    ("09 execution authorized", case_execution_authorized),
    ("10 safety violation", case_safety_violation),
    ("11 policy violation", case_policy_violation),
    ("12 error count mismatch", case_error_count_mismatch),
    ("13 full report copy", case_full_report_copy),
    ("14 output safety", case_output_safety),
    ("15 output policy", case_output_policy),
    ("16 compact metadata", case_compact_metadata),
    ("17 source safety scan", case_source_safety_scan),
]


def main():
    passed = 0

    for name, case in CASES:
        with tempfile.TemporaryDirectory(
            prefix="phase33-"
        ) as directory:
            tmp = Path(directory)

            try:
                case(tmp)
                print(f"[PASS] {name}")
                passed += 1
            except Exception as exc:
                print(f"[FAIL] {name}: {exc}")
                return 1

    print()
    print(
        f"PHASE 33 REGRESSION: "
        f"{passed}/{len(CASES)} PASSED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
