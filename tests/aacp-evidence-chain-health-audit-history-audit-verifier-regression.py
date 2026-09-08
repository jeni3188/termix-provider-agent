#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/aacp-evidence-chain-health-audit-history-audit-verifier.py"

AUDIT_NAME = "latest-aacp-evidence-chain-health-audit-history-audit.json"
HISTORY_NAME = "latest-aacp-evidence-chain-health-audit-history.json"
VERIFY_NAME = "latest-aacp-evidence-chain-health-audit-history-verify.json"
CHAIN_AUDIT_NAME = "latest-aacp-evidence-chain-health-audit.json"
CHAIN_VERIFY_NAME = "latest-aacp-evidence-chain-health-audit-verify.json"
OUTPUT_NAME = "latest-aacp-evidence-chain-health-audit-history-audit-verify.json"

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


def sha(path):
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def base_audit():
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT",
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(SAFE),
        "sideEffects": dict(SAFE),
        "audit": {
            "valid": True,
            "historyExists": True,
            "verifierExists": True,
            "crossLayerValid": True,
        },
        "sources": {},
        "findings": [],
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def base_history():
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(SAFE),
        "sideEffects": dict(SAFE),
        "snapshots": {},
        "consistency": {
            "auditExists": True,
            "verifyExists": True,
            "stateMatch": True,
            "sourceStateMatch": True,
        },
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def base_history_verify():
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_VERIFY",
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(SAFE),
        "sideEffects": dict(SAFE),
        "verification": {
            "valid": True,
            "historyExists": True,
            "auditExists": True,
            "verifyExists": True,
        },
        "sources": {},
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def base_chain_audit():
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT",
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(SAFE),
        "sideEffects": dict(SAFE),
        "audit": {
            "valid": True,
            "findings": [],
            "errors": [],
            "errorCount": 0,
        },
        "sources": {},
        "policy": dict(POLICY),
    }


def base_chain_verify():
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_VERIFY",
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(SAFE),
        "sideEffects": dict(SAFE),
        "verification": {
            "valid": True,
        },
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def setup(tmp, include_all=True):
    audit = base_audit()
    history = base_history()
    history_verify = base_history_verify()
    chain_audit = base_chain_audit()
    chain_verify = base_chain_verify()

    files = {
        AUDIT_NAME: audit,
        HISTORY_NAME: history,
        VERIFY_NAME: history_verify,
        CHAIN_AUDIT_NAME: chain_audit,
        CHAIN_VERIFY_NAME: chain_verify,
    }

    if include_all:
        for name, obj in files.items():
            write(tmp / name, obj)

    audit["sources"] = {
        "history": {
            "file": HISTORY_NAME,
            "exists": True,
            "sha256": sha(tmp / HISTORY_NAME),
        },
        "verifier": {
            "file": VERIFY_NAME,
            "exists": True,
            "sha256": sha(tmp / VERIFY_NAME),
        },
    }

    write(tmp / AUDIT_NAME, audit)


def run(tmp):
    env = dict(os.environ)
    env["AACP_OUTPUT_DIR"] = str(tmp)

    p = subprocess.run(
        ["python3", str(SOURCE)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    out = tmp / OUTPUT_NAME
    obj = json.loads(out.read_text(encoding="utf-8"))

    return p, obj


def expect(name, fn):
    fn()
    print(f"[PASS] {name}")


def case_safe_incomplete(tmp):
    setup(tmp)
    p, obj = run(tmp)
    assert p.returncode == 0
    assert obj["state"] == "INCOMPLETE"
    assert obj["verification"]["valid"] is True


def case_safe_verified(tmp):
    setup(tmp)
    for name in (AUDIT_NAME, HISTORY_NAME, VERIFY_NAME,
                 CHAIN_AUDIT_NAME, CHAIN_VERIFY_NAME):
        obj = json.loads((tmp / name).read_text())
        obj["state"] = "VERIFIED_READ_ONLY"
        obj["sourceState"] = "VERIFIED_READ_ONLY"
        write(tmp / name, obj)

    audit = json.loads((tmp / AUDIT_NAME).read_text())
    audit["sources"]["history"]["sha256"] = sha(tmp / HISTORY_NAME)
    audit["sources"]["verifier"]["sha256"] = sha(tmp / VERIFY_NAME)
    write(tmp / AUDIT_NAME, audit)

    p, obj = run(tmp)
    assert p.returncode == 0
    assert obj["state"] == "VERIFIED_READ_ONLY"
    assert obj["verification"]["valid"] is True


def case_missing_audit(tmp):
    setup(tmp)
    (tmp / AUDIT_NAME).unlink()
    p, obj = run(tmp)
    assert p.returncode != 0
    assert obj["state"] == "BLOCKED"


def case_invalid_audit_json(tmp):
    setup(tmp)
    (tmp / AUDIT_NAME).write_text("{broken", encoding="utf-8")
    p, obj = run(tmp)
    assert p.returncode != 0
    assert obj["state"] == "BLOCKED"


def case_state_mismatch(tmp):
    setup(tmp)
    obj = json.loads((tmp / HISTORY_NAME).read_text())
    obj["state"] = "VERIFIED_READ_ONLY"
    write(tmp / HISTORY_NAME, obj)
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"


def case_source_state_mismatch(tmp):
    setup(tmp)
    obj = json.loads((tmp / HISTORY_NAME).read_text())
    obj["sourceState"] = "VERIFIED_READ_ONLY"
    write(tmp / HISTORY_NAME, obj)
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"


def case_safety_violation(tmp):
    setup(tmp)
    obj = json.loads((tmp / AUDIT_NAME).read_text())
    obj["executionAuthorized"] = True
    write(tmp / AUDIT_NAME, obj)
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"


def case_policy_violation(tmp):
    setup(tmp)
    obj = json.loads((tmp / AUDIT_NAME).read_text())
    obj["policy"]["failClosed"] = False
    write(tmp / AUDIT_NAME, obj)
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"


def case_audit_valid_false(tmp):
    setup(tmp)
    obj = json.loads((tmp / AUDIT_NAME).read_text())
    obj["audit"]["valid"] = False
    write(tmp / AUDIT_NAME, obj)
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"


def case_history_missing(tmp):
    setup(tmp)
    (tmp / HISTORY_NAME).unlink()
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"


def case_verify_missing(tmp):
    setup(tmp)
    (tmp / VERIFY_NAME).unlink()
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"

def case_sha_mismatch(tmp):
    setup(tmp)
    history = json.loads((tmp / HISTORY_NAME).read_text())
    history["generatedAt"] = "2099-12-31T23:59:59Z"
    write(tmp / HISTORY_NAME, history)

    p, report = run(tmp)

    assert p.returncode != 0
    assert report["state"] == "BLOCKED"
    assert any(
        "SHA_MISMATCH" in error
        for error in report["errors"]
    )


def case_cross_layer(tmp):
    setup(tmp)
    obj = json.loads((tmp / HISTORY_VERIFY_FILE).read_text()) if False else None
    chain = json.loads((tmp / CHAIN_AUDIT_NAME).read_text())
    chain["state"] = "VERIFIED_READ_ONLY"
    write(tmp / CHAIN_AUDIT_NAME, chain)
    p, report = run(tmp)
    assert p.returncode != 0
    assert report["state"] == "BLOCKED"


def case_output_safety(tmp):
    setup(tmp)
    p, report = run(tmp)
    assert p.returncode == 0
    assert report["executionAuthorized"] is False
    assert report["safety"] == SAFE
    assert report["sideEffects"] == SAFE


def case_output_policy(tmp):
    setup(tmp)
    p, report = run(tmp)
    assert p.returncode == 0
    assert report["policy"] == POLICY


def case_compact_metadata(tmp):
    setup(tmp)
    p, report = run(tmp)
    assert p.returncode == 0

    for key in ("audit", "history", "verifier"):
        src = report["sources"][key]
        assert set(src.keys()) == {"file", "exists", "sha256"}

    assert "content" not in report
    assert "report" not in report


def case_source_scan(tmp):
    text = SOURCE.read_text(encoding="utf-8").lower()

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
        assert token not in text, f"forbidden primitive found: {token}"


def main():
    cases = [
        ("01 safe incomplete -> INCOMPLETE", case_safe_incomplete),
        ("02 safe verified -> VERIFIED_READ_ONLY", case_safe_verified),
        ("03 missing audit -> BLOCKED", case_missing_audit),
        ("04 invalid audit JSON -> BLOCKED", case_invalid_audit_json),
        ("05 state mismatch -> BLOCKED", case_state_mismatch),
        ("06 sourceState mismatch -> BLOCKED", case_source_state_mismatch),
        ("07 safety violation -> BLOCKED", case_safety_violation),
        ("08 policy violation -> BLOCKED", case_policy_violation),
        ("09 audit.valid violation -> BLOCKED", case_audit_valid_false),
        ("10 history missing -> BLOCKED", case_history_missing),
        ("11 verifier missing -> BLOCKED", case_verify_missing),
        ("12 SHA mismatch -> BLOCKED", case_sha_mismatch),
        ("13 cross-layer mismatch -> BLOCKED", case_cross_layer),
        ("14 output safety invariants", case_output_safety),
        ("15 output policy fail closed", case_output_policy),
        ("16 compact metadata + SHA only", case_compact_metadata),
        ("17 source safety scan", case_source_scan),
    ]

    passed = 0

    for label, fn in cases:
        with tempfile.TemporaryDirectory(prefix="phase30-") as d:
            tmp = Path(d)
            try:
                fn(tmp)
                print(f"[PASS] {label}")
                passed += 1
            except Exception as exc:
                print(f"[FAIL] {label}: {exc}")
                raise

    print()
    print(f"PHASE 30 REGRESSION: {passed}/{len(cases)} PASSED")


if __name__ == "__main__":
    main()
