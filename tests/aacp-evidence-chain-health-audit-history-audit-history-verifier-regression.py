#!/usr/bin/env python3

import json
import os
import subprocess
import tempfile
from pathlib import Path


SOURCE = Path(
    "src/aacp-evidence-chain-health-audit-history-audit-history-verifier.py"
)

SOURCE_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-"
    "audit-history.json"
)

OUTPUT_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-"
    "audit-history-verify.json"
)

AUDIT_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit.json"
)

VERIFY_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-verify.json"
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2) + "\n",
        encoding="utf-8",
    )


def base(type_name, state="INCOMPLETE"):
    return {
        "version": "1.0.0",
        "type": type_name,
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": state,
        "executionAuthorized": False,
        "safety": dict(SAFE),
        "sideEffects": dict(SAFE),
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def make_audit():
    obj = base(
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT"
    )
    obj["audit"] = {
        "valid": True,
        "historyExists": True,
        "verifierExists": True,
        "crossLayerValid": True,
    }
    return obj


def make_verify():
    return base(
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_VERIFY"
    )


def make_source(tmp):
    audit = tmp / AUDIT_NAME
    verify = tmp / VERIFY_NAME

    write(audit, make_audit())
    write(verify, make_verify())

    def sha(path):
        import hashlib
        return hashlib.sha256(path.read_bytes()).hexdigest()

    source = base(
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY"
    )

    source["snapshots"] = {
        "audit": {
            "file": audit.name,
            "exists": True,
            "sha256": sha(audit),
            "state": "INCOMPLETE",
            "sourceState": "INCOMPLETE",
            "executionAuthorized": False,
            "errorCount": 0,
        },
        "verify": {
            "file": verify.name,
            "exists": True,
            "sha256": sha(verify),
            "state": "INCOMPLETE",
            "sourceState": "INCOMPLETE",
            "executionAuthorized": False,
            "errorCount": 0,
        },
    }

    source["consistency"] = {
        "auditExists": True,
        "verifyExists": True,
        "stateMatch": True,
        "sourceStateMatch": True,
    }

    write(tmp / SOURCE_NAME, source)


def run(tmp):
    env = os.environ.copy()
    env["AACP_OUTPUT_DIR"] = str(tmp)

    return subprocess.run(
        ["python3", str(SOURCE)],
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


def case_safe(tmp):
    make_source(tmp)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["state"] == "INCOMPLETE"
    assert r["verification"]["valid"] is True


def case_verified(tmp):
    make_source(tmp)

    audit_path = tmp / AUDIT_NAME
    verify_path = tmp / VERIFY_NAME

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    verify = json.loads(verify_path.read_text(encoding="utf-8"))

    audit["state"] = "VERIFIED_READ_ONLY"
    audit["sourceState"] = "VERIFIED_READ_ONLY"

    verify["state"] = "VERIFIED_READ_ONLY"
    verify["sourceState"] = "VERIFIED_READ_ONLY"

    write(audit_path, audit)
    write(verify_path, verify)

    import hashlib

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    source = json.loads(
        (tmp / SOURCE_NAME).read_text(encoding="utf-8")
    )

    source["state"] = "VERIFIED_READ_ONLY"
    source["sourceState"] = "VERIFIED_READ_ONLY"

    for key, path in (
        ("audit", audit_path),
        ("verify", verify_path),
    ):
        source["snapshots"][key]["sha256"] = sha(path)
        source["snapshots"][key]["state"] = "VERIFIED_READ_ONLY"
        source["snapshots"][key]["sourceState"] = "VERIFIED_READ_ONLY"

    source["consistency"] = {
        "auditExists": True,
        "verifyExists": True,
        "stateMatch": True,
        "sourceStateMatch": True,
    }

    write(tmp / SOURCE_NAME, source)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["state"] == "VERIFIED_READ_ONLY"
    assert r["sourceState"] == "VERIFIED_READ_ONLY"
    assert r["verification"]["valid"] is True


def case_missing_source(tmp):
    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "SOURCE_MISSING" in r["errors"]


def case_invalid_json(tmp):
    make_source(tmp)

    (tmp / SOURCE_NAME).write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "SOURCE_INVALID_JSON" in r["errors"]


def case_execution_authorized(tmp):
    make_source(tmp)

    source = json.loads(
        (tmp / SOURCE_NAME).read_text()
    )
    source["executionAuthorized"] = True
    write(tmp / SOURCE_NAME, source)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "EXECUTION_AUTHORIZED" in r["errors"]


def case_safety_violation(tmp):
    make_source(tmp)

    source = json.loads(
        (tmp / SOURCE_NAME).read_text()
    )
    source["safety"]["broadcastPerformed"] = True
    write(tmp / SOURCE_NAME, source)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "SAFETY_VIOLATION" in r["errors"]


def case_policy_violation(tmp):
    make_source(tmp)

    source = json.loads(
        (tmp / SOURCE_NAME).read_text()
    )
    source["policy"]["failClosed"] = False
    write(tmp / SOURCE_NAME, source)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "POLICY_VIOLATION" in r["errors"]


def case_sha_tamper(tmp):
    make_source(tmp)

    audit = tmp / AUDIT_NAME
    obj = json.loads(audit.read_text())
    obj["generatedAt"] = "2099-12-31T23:59:59Z"
    write(audit, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "SNAPSHOT_AUDIT_SHA_MISMATCH" in r["errors"]


def case_state_tamper(tmp):
    make_source(tmp)

    audit = tmp / AUDIT_NAME
    obj = json.loads(audit.read_text())
    obj["state"] = "VERIFIED_READ_ONLY"
    write(audit, obj)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "SNAPSHOT_AUDIT_SHA_MISMATCH" in r["errors"]


def case_snapshot_fields(tmp):
    make_source(tmp)

    source = json.loads(
        (tmp / SOURCE_NAME).read_text()
    )
    del source["snapshots"]["audit"]["sha256"]
    write(tmp / SOURCE_NAME, source)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "SNAPSHOT_AUDIT_FIELDS_INVALID" in r["errors"]


def case_consistency(tmp):
    make_source(tmp)

    source = json.loads(
        (tmp / SOURCE_NAME).read_text()
    )
    source["consistency"]["stateMatch"] = False
    write(tmp / SOURCE_NAME, source)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "CONSISTENCY_STATE_MATCH_MISMATCH" in r["errors"]


def case_error_count(tmp):
    make_source(tmp)

    source = json.loads(
        (tmp / SOURCE_NAME).read_text()
    )
    source["errorCount"] = 99
    write(tmp / SOURCE_NAME, source)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "ERROR_COUNT_MISMATCH" in r["errors"]


def case_output_safety(tmp):
    make_source(tmp)

    run(tmp)
    r = report(tmp)

    assert r["executionAuthorized"] is False
    assert r["safety"] == SAFE
    assert r["sideEffects"] == SAFE


def case_output_policy(tmp):
    make_source(tmp)

    run(tmp)
    r = report(tmp)

    assert r["policy"] == POLICY


def case_compact_output(tmp):
    make_source(tmp)

    run(tmp)
    r = report(tmp)

    assert set(r["sources"]["auditHistory"]) == {
        "file",
        "exists",
        "sha256",
    }

    assert "content" not in r
    assert "report" not in r
    assert "fullReport" not in r


def case_source_scan(tmp):
    text = SOURCE.read_text(
        encoding="utf-8"
    ).lower()

    forbidden = [
        "import requests",
        "import urllib",
        "import websocket",
        "import socket",
        "import subprocess",
        "os.system(",
        "os.popen(",
        "requests.",
        "urllib.",
        "websocket.",
        "socket.",
        "sign(",
        "broadcast(",
        "submit(",
        "mnemonic access",
        "executor actions",
    ]

    for token in forbidden:
        assert token not in text, token


CASES = [
    ("01 safe incomplete", case_safe),
    ("02 safe verified", case_verified),
    ("03 missing source", case_missing_source),
    ("04 invalid JSON", case_invalid_json),
    ("05 execution authorized", case_execution_authorized),
    ("06 safety violation", case_safety_violation),
    ("07 policy violation", case_policy_violation),
    ("08 SHA tamper", case_sha_tamper),
    ("09 state tamper", case_state_tamper),
    ("10 snapshot fields", case_snapshot_fields),
    ("11 consistency mismatch", case_consistency),
    ("12 error count mismatch", case_error_count),
    ("13 output safety invariants", case_output_safety),
    ("14 output policy", case_output_policy),
    ("15 compact metadata", case_compact_output),
    ("16 source safety scan", case_source_scan),
]


def main():
    passed = 0

    for label, fn in CASES:
        with tempfile.TemporaryDirectory(
            prefix="phase32-"
        ) as directory:
            tmp = Path(directory)

            try:
                fn(tmp)
                print(f"[PASS] {label}")
                passed += 1
            except Exception as exc:
                print(f"[FAIL] {label}: {exc}")
                raise

    print()
    print(
        f"PHASE 32 REGRESSION: "
        f"{passed}/{len(CASES)} PASSED"
    )


if __name__ == "__main__":
    main()
