#!/usr/bin/env python3
"""
Regression suite for:
AACP Evidence Chain Health Audit History Auditor

21 safety/integrity scenarios.

The suite creates isolated temporary AACP_OUTPUT_DIR trees,
executes the auditor, and verifies both exit state and output.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/aacp-evidence-chain-health-audit-history-auditor.py"

AUDIT_NAME = "latest-aacp-evidence-chain-health-audit.json"
VERIFY_NAME = "latest-aacp-evidence-chain-health-audit-verify.json"
HISTORY_NAME = "latest-aacp-evidence-chain-health-audit-history.json"
VERIFIER_NAME = "latest-aacp-evidence-chain-health-audit-history-verify.json"
OUTPUT_NAME = "latest-aacp-evidence-chain-health-audit-history-audit.json"


FALSE_SAFETY = {
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj: dict) -> None:
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def audit_obj(state="INCOMPLETE", source_state="INCOMPLETE") -> dict:
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(FALSE_SAFETY),
        "sideEffects": dict(FALSE_SAFETY),
        "sources": {},
        "audit": {
            "valid": True,
            "findings": [],
            "errors": [],
            "errorCount": 0,
        },
        "policy": dict(POLICY),
    }


def verify_obj(state="INCOMPLETE", source_state="INCOMPLETE") -> dict:
    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_VERIFY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(FALSE_SAFETY),
        "sideEffects": dict(FALSE_SAFETY),
        "verification": {
            "valid": True,
            "auditExists": True,
            "verifyExists": True,
        },
        "sources": {},
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def make_history(
    root: Path,
    state="INCOMPLETE",
    source_state="INCOMPLETE",
) -> dict:
    audit_path = root / AUDIT_NAME
    verify_path = root / VERIFY_NAME

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    verify = json.loads(verify_path.read_text(encoding="utf-8"))

    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(FALSE_SAFETY),
        "sideEffects": dict(FALSE_SAFETY),
        "snapshots": {
            "audit": {
                "file": AUDIT_NAME,
                "exists": True,
                "sha256": sha256(audit_path),
                "state": audit["state"],
                "sourceState": audit["sourceState"],
                "auditValid": True,
                "errorCount": 0,
            },
            "verify": {
                "file": VERIFY_NAME,
                "exists": True,
                "sha256": sha256(verify_path),
                "state": verify["state"],
                "sourceState": verify["sourceState"],
                "verificationValid": True,
                "errorCount": 0,
            },
        },
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


def make_verifier(
    root: Path,
    history: dict,
    audit: dict,
    verify: dict,
) -> dict:
    history_path = root / HISTORY_NAME
    audit_path = root / AUDIT_NAME
    verify_path = root / VERIFY_NAME

    # History must already exist for normal verifier generation.
    write_json(history_path, history)

    return {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_VERIFY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": history["state"],
        "sourceState": history["sourceState"],
        "executionAuthorized": False,
        "safety": dict(FALSE_SAFETY),
        "sideEffects": dict(FALSE_SAFETY),
        "verification": {
            "valid": True,
            "historyExists": True,
            "auditExists": True,
            "verifyExists": True,
        },
        "sources": {
            "history": {
                "file": HISTORY_NAME,
                "exists": True,
                "sha256": sha256(history_path),
            },
            "audit": {
                "file": AUDIT_NAME,
                "exists": True,
                "sha256": sha256(audit_path),
            },
            "verify": {
                "file": VERIFY_NAME,
                "exists": True,
                "sha256": sha256(verify_path),
            },
        },
        "errors": [],
        "errorCount": 0,
        "policy": dict(POLICY),
    }


def run_case(
    setup,
    expected_state,
    expected_exit,
    expected_error=None,
):
    tmp = Path(tempfile.mkdtemp(prefix="termix-phase29-"))

    try:
        setup(tmp)

        env = os.environ.copy()
        env["AACP_OUTPUT_DIR"] = str(tmp)

        proc = subprocess.run(
            ["python", str(SOURCE)],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
        )

        output = tmp / OUTPUT_NAME

        assert output.exists(), (
            f"output missing\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )

        data = json.loads(output.read_text(encoding="utf-8"))

        assert data["state"] == expected_state, (
            f"state expected {expected_state}, "
            f"got {data['state']}\n"
            f"stdout={proc.stdout}\n"
            f"stderr={proc.stderr}"
        )

        assert proc.returncode == expected_exit, (
            f"exit expected {expected_exit}, "
            f"got {proc.returncode}\n"
            f"stdout={proc.stdout}\n"
            f"stderr={proc.stderr}"
        )

        if expected_error:
            assert expected_error in data["errors"], (
                f"missing expected error {expected_error}: "
                f"{data['errors']}"
            )

        return data

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def safe_complete_setup(state="INCOMPLETE"):
    def setup(root: Path):
        audit = audit_obj(state, state)
        verify = verify_obj(state, state)

        write_json(root / AUDIT_NAME, audit)
        write_json(root / VERIFY_NAME, verify)

        history = make_history(root, state, state)
        write_json(root / HISTORY_NAME, history)

        verifier = make_verifier(root, history, audit, verify)
        write_json(root / VERIFIER_NAME, verifier)

    return setup


def case_missing_history(root):
    audit = audit_obj()
    verify = verify_obj()
    write_json(root / AUDIT_NAME, audit)
    write_json(root / VERIFY_NAME, verify)


def case_missing_verifier(root):
    audit = audit_obj()
    verify = verify_obj()

    write_json(root / AUDIT_NAME, audit)
    write_json(root / VERIFY_NAME, verify)

    history = make_history(root)
    write_json(root / HISTORY_NAME, history)


def case_missing_audit(root):
    verify = verify_obj()
    write_json(root / VERIFY_NAME, verify)

    history = {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(FALSE_SAFETY),
        "sideEffects": dict(FALSE_SAFETY),
        "snapshots": {
            "audit": {
                "file": AUDIT_NAME,
                "exists": True,
                "sha256": "deadbeef",
                "state": "INCOMPLETE",
                "sourceState": "INCOMPLETE",
                "valid": True,
                "errorCount": 0,
            },
            "verify": {
                "file": VERIFY_NAME,
                "exists": True,
                "sha256": sha256(root / VERIFY_NAME),
                "state": "INCOMPLETE",
                "sourceState": "INCOMPLETE",
                "valid": True,
                "errorCount": 0,
            },
        },
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

    write_json(root / HISTORY_NAME, history)


def case_missing_verify(root):
    audit = audit_obj()
    write_json(root / AUDIT_NAME, audit)

    history = {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "mode": "READ_ONLY",
        "state": "INCOMPLETE",
        "sourceState": "INCOMPLETE",
        "executionAuthorized": False,
        "safety": dict(FALSE_SAFETY),
        "sideEffects": dict(FALSE_SAFETY),
        "snapshots": {
            "audit": {
                "file": AUDIT_NAME,
                "exists": True,
                "sha256": sha256(root / AUDIT_NAME),
                "state": "INCOMPLETE",
                "sourceState": "INCOMPLETE",
                "valid": True,
                "errorCount": 0,
            },
            "verify": {
                "file": VERIFY_NAME,
                "exists": True,
                "sha256": "deadbeef",
                "state": "INCOMPLETE",
                "sourceState": "INCOMPLETE",
                "valid": True,
                "errorCount": 0,
            },
        },
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

    write_json(root / HISTORY_NAME, history)


def case_history_sha_mismatch(root):
    safe_complete_setup()(root)

    history_path = root / HISTORY_NAME
    history = json.loads(history_path.read_text(encoding="utf-8"))
    history["snapshots"]["audit"]["sha256"] = "00" * 32
    write_json(history_path, history)


def case_history_state_mismatch(root):
    safe_complete_setup()(root)

    history_path = root / HISTORY_NAME
    history = json.loads(history_path.read_text(encoding="utf-8"))
    history["snapshots"]["audit"]["state"] = "VERIFIED_READ_ONLY"
    write_json(history_path, history)


def case_history_source_state_mismatch(root):
    safe_complete_setup()(root)

    history_path = root / HISTORY_NAME
    history = json.loads(history_path.read_text(encoding="utf-8"))
    history["snapshots"]["audit"]["sourceState"] = "VERIFIED_READ_ONLY"
    write_json(history_path, history)


def case_verifier_state_mismatch(root):
    safe_complete_setup()(root)

    verifier_path = root / VERIFIER_NAME
    verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
    verifier["state"] = "VERIFIED_READ_ONLY"
    write_json(verifier_path, verifier)


def case_verifier_source_state_mismatch(root):
    safe_complete_setup()(root)

    verifier_path = root / VERIFIER_NAME
    verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
    verifier["sourceState"] = "VERIFIED_READ_ONLY"
    write_json(verifier_path, verifier)


def case_history_safety(root):
    safe_complete_setup()(root)

    path = root / HISTORY_NAME
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["safety"]["walletUsed"] = True
    write_json(path, obj)


def case_history_policy(root):
    safe_complete_setup()(root)

    path = root / HISTORY_NAME
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["policy"]["failClosed"] = False
    write_json(path, obj)


def case_verifier_safety(root):
    safe_complete_setup()(root)

    path = root / VERIFIER_NAME
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["safety"]["signingPerformed"] = True
    write_json(path, obj)


def case_verifier_policy(root):
    safe_complete_setup()(root)

    path = root / VERIFIER_NAME
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["policy"]["post"] = "PERFORMED"
    write_json(path, obj)


def case_invalid_history(root):
    safe_complete_setup()(root)
    (root / HISTORY_NAME).write_text("{broken\n", encoding="utf-8")


def case_invalid_verifier(root):
    safe_complete_setup()(root)
    (root / VERIFIER_NAME).write_text("{broken\n", encoding="utf-8")


def case_output_safety(root):
    data = run_case(
        safe_complete_setup(),
        "INCOMPLETE",
        0,
    )

    assert data["executionAuthorized"] is False
    assert data["safety"] == FALSE_SAFETY
    assert data["sideEffects"] == FALSE_SAFETY


def case_output_policy(root):
    data = run_case(
        safe_complete_setup(),
        "INCOMPLETE",
        0,
    )

    assert data["policy"] == POLICY


def case_compact_output(root):
    data = run_case(
        safe_complete_setup(),
        "INCOMPLETE",
        0,
    )

    assert "raw" not in data
    assert "content" not in data
    assert "reportCopy" not in data

    assert set(data["sources"].keys()) == {
        "history",
        "verifier",
    }

    for item in data["sources"].values():
        assert set(item.keys()) == {
            "file",
            "exists",
            "sha256",
        }


def case_source_scan():
    text = SOURCE.read_text(encoding="utf-8")

    forbidden = [
        "requests.",
        "urllib.",
        "http.client",
        "httpx.",
        "aiohttp.",
        "websocket",
        "WebSocket",
        "fetch(",
        "axios",
        "socket.",
        "subprocess",
        "private_key",
        "privateKey",
        "mnemonic",
        "seed_phrase",
        "signTransaction",
        "sign_transaction",
        "broadcastTransaction",
        "broadcast_transaction",
        "sendTransaction",
        "send_transaction",
        "submitTransaction",
        "submit_transaction",
        "executor",
        "EXECUTOR",
    ]

    # This source intentionally contains no subprocess/network primitives.
    for token in forbidden:
        assert token not in text, (
            f"forbidden primitive found in auditor source: {token}"
        )


def main():
    passed = 0
    total = 21

    # 1 safe incomplete
    data = run_case(safe_complete_setup(), "INCOMPLETE", 0)
    assert data["audit"]["valid"] is True
    passed += 1
    print("[PASS] 01 safe incomplete -> INCOMPLETE")

    # 2 safe verified
    data = run_case(
        safe_complete_setup("VERIFIED_READ_ONLY"),
        "VERIFIED_READ_ONLY",
        0,
    )
    assert data["audit"]["valid"] is True
    passed += 1
    print("[PASS] 02 safe verified -> VERIFIED_READ_ONLY")

    # 3 missing history
    data = run_case(
        case_missing_history,
        "BLOCKED",
        1,
        "HISTORY_MISSING",
    )
    passed += 1
    print("[PASS] 03 missing history -> BLOCKED")

    # 4 missing verifier
    data = run_case(
        case_missing_verifier,
        "BLOCKED",
        1,
        "VERIFIER_MISSING",
    )
    passed += 1
    print("[PASS] 04 missing verifier -> BLOCKED")

    # 5 missing audit source
    data = run_case(
        case_missing_audit,
        "BLOCKED",
        1,
    )
    passed += 1
    print("[PASS] 05 missing audit source -> BLOCKED")

    # 6 missing verify source
    data = run_case(
        case_missing_verify,
        "BLOCKED",
        1,
    )
    passed += 1
    print("[PASS] 06 missing verify source -> BLOCKED")

    # 7 history SHA mismatch
    data = run_case(
        case_history_sha_mismatch,
        "BLOCKED",
        1,
        "HISTORY_AUDIT_SHA256_MISMATCH",
    )
    passed += 1
    print("[PASS] 07 history SHA mismatch -> BLOCKED")

    # 8 history state linkage
    data = run_case(
        case_history_state_mismatch,
        "BLOCKED",
        1,
        "HISTORY_AUDIT_STATE_LINK_MISMATCH",
    )
    passed += 1
    print("[PASS] 08 history state linkage -> BLOCKED")

    # 9 history sourceState linkage
    data = run_case(
        case_history_source_state_mismatch,
        "BLOCKED",
        1,
        "HISTORY_AUDIT_SOURCE_STATE_LINK_MISMATCH",
    )
    passed += 1
    print("[PASS] 09 history sourceState linkage -> BLOCKED")

    # 10 verifier state mismatch
    data = run_case(
        case_verifier_state_mismatch,
        "BLOCKED",
        1,
        "VERIFIER_HISTORY_STATE_MISMATCH",
    )
    passed += 1
    print("[PASS] 10 verifier state mismatch -> BLOCKED")

    # 11 verifier sourceState mismatch
    data = run_case(
        case_verifier_source_state_mismatch,
        "BLOCKED",
        1,
        "VERIFIER_HISTORY_SOURCE_STATE_MISMATCH",
    )
    passed += 1
    print("[PASS] 11 verifier sourceState mismatch -> BLOCKED")

    # 12 history safety
    data = run_case(
        case_history_safety,
        "BLOCKED",
        1,
        "SAFETY_VIOLATION",
    )
    passed += 1
    print("[PASS] 12 history safety violation -> BLOCKED")

    # 13 history policy
    data = run_case(
        case_history_policy,
        "BLOCKED",
        1,
        "POLICY_VIOLATION",
    )
    passed += 1
    print("[PASS] 13 history policy violation -> BLOCKED")

    # 14 verifier safety
    data = run_case(
        case_verifier_safety,
        "BLOCKED",
        1,
        "SAFETY_VIOLATION",
    )
    passed += 1
    print("[PASS] 14 verifier safety violation -> BLOCKED")

    # 15 verifier policy
    data = run_case(
        case_verifier_policy,
        "BLOCKED",
        1,
        "POLICY_VIOLATION",
    )
    passed += 1
    print("[PASS] 15 verifier policy violation -> BLOCKED")

    # 16 invalid history JSON
    data = run_case(
        case_invalid_history,
        "BLOCKED",
        1,
        "HISTORY_INVALID_JSON",
    )
    passed += 1
    print("[PASS] 16 invalid history JSON -> BLOCKED")

    # 17 invalid verifier JSON
    data = run_case(
        case_invalid_verifier,
        "BLOCKED",
        1,
        "VERIFIER_INVALID_JSON",
    )
    passed += 1
    print("[PASS] 17 invalid verifier JSON -> BLOCKED")

    # 18 output safety invariants
    tmp = Path(tempfile.mkdtemp(prefix="termix-phase29-output-safety-"))
    try:
        env = os.environ.copy()
        env["AACP_OUTPUT_DIR"] = str(tmp)

        setup = safe_complete_setup()
        setup(tmp)

        proc = subprocess.run(
            ["python", str(SOURCE)],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
        )

        assert proc.returncode == 0

        output = json.loads(
            (tmp / OUTPUT_NAME).read_text(encoding="utf-8")
        )

        assert output["executionAuthorized"] is False
        assert output["safety"] == FALSE_SAFETY
        assert output["sideEffects"] == FALSE_SAFETY

        passed += 1
        print("[PASS] 18 output safety invariants remain false")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 19 output policy
    tmp = Path(tempfile.mkdtemp(prefix="termix-phase29-output-policy-"))
    try:
        safe_complete_setup()(tmp)

        env = os.environ.copy()
        env["AACP_OUTPUT_DIR"] = str(tmp)

        proc = subprocess.run(
            ["python", str(SOURCE)],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
        )

        assert proc.returncode == 0

        output = json.loads(
            (tmp / OUTPUT_NAME).read_text(encoding="utf-8")
        )

        assert output["policy"] == POLICY

        passed += 1
        print("[PASS] 19 output policy remains fail closed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 20 compact metadata + SHA only
    tmp = Path(tempfile.mkdtemp(prefix="termix-phase29-compact-"))
    try:
        safe_complete_setup()(tmp)

        env = os.environ.copy()
        env["AACP_OUTPUT_DIR"] = str(tmp)

        proc = subprocess.run(
            ["python", str(SOURCE)],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
        )

        assert proc.returncode == 0

        output = json.loads(
            (tmp / OUTPUT_NAME).read_text(encoding="utf-8")
        )

        assert "raw" not in output
        assert "content" not in output
        assert "reportCopy" not in output

        assert set(output["sources"].keys()) == {
            "history",
            "verifier",
        }

        for item in output["sources"].values():
            assert set(item.keys()) == {
                "file",
                "exists",
                "sha256",
            }

        passed += 1
        print("[PASS] 20 output compact metadata + SHA only")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 21 source safety scan
    case_source_scan()
    passed += 1
    print("[PASS] 21 source has no network/signing/execution primitives")

    print()
    print(f"PHASE 29 REGRESSION: {passed}/{total} PASSED")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
