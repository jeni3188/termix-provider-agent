#!/usr/bin/env python3

import json
import os
import subprocess
import tempfile
from pathlib import Path


SOURCE = Path(
    "src/aacp-evidence-chain-health-audit-history-audit-history.py"
)

AUDIT_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit.json"
)

VERIFY_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-verify.json"
)

OUTPUT_NAME = (
    "latest-aacp-evidence-chain-health-audit-history-audit-history.json"
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


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2) + "\n",
        encoding="utf-8",
    )


def base(
    type_name,
    state="INCOMPLETE",
    source_state="INCOMPLETE",
):
    return {
        "version": "1.0.0",
        "type": type_name,
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(SAFETY),
        "sideEffects": dict(SAFETY),
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


def setup(tmp):
    audit = tmp / AUDIT_NAME
    verify = tmp / VERIFY_NAME

    write(audit, make_audit())
    write(verify, make_verify())


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


def case_safe_incomplete(tmp):
    setup(tmp)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["state"] == "INCOMPLETE"
    assert r["sourceState"] == "INCOMPLETE"
    assert r["errorCount"] == 0


def case_safe_verified(tmp):
    setup(tmp)

    audit = json.loads(
        (tmp / AUDIT_NAME).read_text()
    )
    verify = json.loads(
        (tmp / VERIFY_NAME).read_text()
    )

    audit["state"] = "VERIFIED_READ_ONLY"
    audit["sourceState"] = "VERIFIED_READ_ONLY"

    verify["state"] = "VERIFIED_READ_ONLY"
    verify["sourceState"] = "VERIFIED_READ_ONLY"

    write(tmp / AUDIT_NAME, audit)
    write(tmp / VERIFY_NAME, verify)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode == 0
    assert r["state"] == "VERIFIED_READ_ONLY"
    assert r["errorCount"] == 0


def case_missing_audit(tmp):
    setup(tmp)
    (tmp / AUDIT_NAME).unlink()

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "AUDIT_MISSING" in r["errors"]


def case_missing_verify(tmp):
    setup(tmp)
    (tmp / VERIFY_NAME).unlink()

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "VERIFY_MISSING" in r["errors"]


def case_invalid_audit_json(tmp):
    setup(tmp)
    (tmp / AUDIT_NAME).write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "AUDIT_INVALID_JSON" in r["errors"]


def case_invalid_verify_json(tmp):
    setup(tmp)
    (tmp / VERIFY_NAME).write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "VERIFY_INVALID_JSON" in r["errors"]


def case_state_mismatch(tmp):
    setup(tmp)

    verify = json.loads(
        (tmp / VERIFY_NAME).read_text()
    )
    verify["state"] = "VERIFIED_READ_ONLY"

    write(tmp / VERIFY_NAME, verify)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "STATE_MISMATCH" in r["errors"]


def case_source_state_mismatch(tmp):
    setup(tmp)

    verify = json.loads(
        (tmp / VERIFY_NAME).read_text()
    )
    verify["sourceState"] = "VERIFIED_READ_ONLY"

    write(tmp / VERIFY_NAME, verify)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert "SOURCE_STATE_MISMATCH" in r["errors"]


def case_audit_valid_violation(tmp):
    setup(tmp)

    audit = json.loads(
        (tmp / AUDIT_NAME).read_text()
    )
    audit["audit"]["valid"] = False

    write(tmp / AUDIT_NAME, audit)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert any(
        "AUDIT_VALID_INVALID" in e
        for e in r["errors"]
    )


def case_history_exists_violation(tmp):
    setup(tmp)

    audit = json.loads(
        (tmp / AUDIT_NAME).read_text()
    )
    audit["audit"]["historyExists"] = False

    write(tmp / AUDIT_NAME, audit)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert any(
        "AUDIT_HISTORYEXISTS_INVALID" in e
        for e in r["errors"]
    )


def case_verifier_exists_violation(tmp):
    setup(tmp)

    audit = json.loads(
        (tmp / AUDIT_NAME).read_text()
    )
    audit["audit"]["verifierExists"] = False

    write(tmp / AUDIT_NAME, audit)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert any(
        "AUDIT_VERIFIEREXISTS_INVALID" in e
        for e in r["errors"]
    )


def case_cross_layer_violation(tmp):
    setup(tmp)

    audit = json.loads(
        (tmp / AUDIT_NAME).read_text()
    )
    audit["audit"]["crossLayerValid"] = False

    write(tmp / AUDIT_NAME, audit)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"
    assert any(
        "AUDIT_CROSSLAYERVALID_INVALID" in e
        for e in r["errors"]
    )


def case_execution_authorized(tmp):
    setup(tmp)

    audit = json.loads(
        (tmp / AUDIT_NAME).read_text()
    )
    audit["executionAuthorized"] = True

    write(tmp / AUDIT_NAME, audit)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_safety_violation(tmp):
    setup(tmp)

    audit = json.loads(
        (tmp / AUDIT_NAME).read_text()
    )
    audit["safety"]["broadcastPerformed"] = True

    write(tmp / AUDIT_NAME, audit)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_policy_violation(tmp):
    setup(tmp)

    verify = json.loads(
        (tmp / VERIFY_NAME).read_text()
    )
    verify["policy"]["failClosed"] = False

    write(tmp / VERIFY_NAME, verify)

    p = run(tmp)
    r = report(tmp)

    assert p.returncode != 0
    assert r["state"] == "BLOCKED"


def case_output_safety(tmp):
    setup(tmp)

    run(tmp)
    r = report(tmp)

    assert r["executionAuthorized"] is False
    assert r["safety"] == SAFETY
    assert r["sideEffects"] == SAFETY


def case_output_policy(tmp):
    setup(tmp)

    run(tmp)
    r = report(tmp)

    assert r["policy"] == POLICY


def case_compact_snapshot(tmp):
    setup(tmp)

    run(tmp)
    r = report(tmp)

    assert set(r["snapshots"]["audit"]) == {
        "file",
        "exists",
        "sha256",
        "state",
        "sourceState",
        "executionAuthorized",
        "errorCount",
    }

    assert set(r["snapshots"]["verify"]) == {
        "file",
        "exists",
        "sha256",
        "state",
        "sourceState",
        "executionAuthorized",
        "errorCount",
    }


def case_source_safety_scan(tmp):
    text = SOURCE.read_text(
        encoding="utf-8"
    ).lower()

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

    for token in forbidden:
        assert token not in text, token


CASES = [
    ("01 safe incomplete -> INCOMPLETE", case_safe_incomplete),
    ("02 safe verified -> VERIFIED_READ_ONLY", case_safe_verified),
    ("03 missing audit -> BLOCKED", case_missing_audit),
    ("04 missing verify -> BLOCKED", case_missing_verify),
    ("05 invalid audit JSON -> BLOCKED", case_invalid_audit_json),
    ("06 invalid verify JSON -> BLOCKED", case_invalid_verify_json),
    ("07 state mismatch -> BLOCKED", case_state_mismatch),
    ("08 sourceState mismatch -> BLOCKED", case_source_state_mismatch),
    ("09 audit.valid violation -> BLOCKED", case_audit_valid_violation),
    ("10 historyExists violation -> BLOCKED", case_history_exists_violation),
    ("11 verifierExists violation -> BLOCKED", case_verifier_exists_violation),
    ("12 crossLayerValid violation -> BLOCKED", case_cross_layer_violation),
    ("13 execution authorized -> BLOCKED", case_execution_authorized),
    ("14 safety violation -> BLOCKED", case_safety_violation),
    ("15 policy violation -> BLOCKED", case_policy_violation),
    ("16 output safety invariants", case_output_safety),
    ("17 output policy fail closed", case_output_policy),
    ("18 compact metadata + SHA only", case_compact_snapshot),
    ("19 source safety scan", case_source_safety_scan),
]


def main():
    passed = 0

    for label, fn in CASES:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)

            try:
                fn(tmp)
                print(f"[PASS] {label}")
                passed += 1
            except Exception as exc:
                print(
                    f"[FAIL] {label}: {exc}"
                )
                raise

    print(
        f"\nPHASE 31 REGRESSION: "
        f"{passed}/{len(CASES)} PASSED"
    )


if __name__ == "__main__":
    main()
