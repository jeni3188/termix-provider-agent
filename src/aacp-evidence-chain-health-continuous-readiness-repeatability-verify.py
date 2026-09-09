#!/usr/bin/env python3

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OBSERVER_DIR = BASE_DIR / "provider-output" / "aacp-observer"

PHASE37_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json"
)

OUTPUT_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json"
)

BASELINE_FILE = (
    OBSERVER_DIR
    / "aacp-evidence-chain-health-post-readiness-drift-baseline.json"
)

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CONTINUOUS_READINESS_REPEATABILITY_VERIFY"

LAYERS = {
    "phase31": (
        "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
    ),
    "phase32": (
        "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
    ),
    "phase33": (
        "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
    ),
    "phase34": (
        "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-integrity-attestation.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
    ),
    "phase35": (
        "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
    ),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def fail_result(errors, layers=None):
    if layers is None:
        layers = {name: "BLOCKED" for name in LAYERS}

    return {
        "state": "BLOCKED",
        "sourceState": "BLOCKED",
        "executionAuthorized": False,
        "safety": {
            "postPerformed": False,
            "walletUsed": False,
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
        },
        "sideEffects": {
            "network": False,
            "filesystemWrite": True,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "readiness": {
            "ready": False,
            "reason": "CONTINUOUS_READINESS_REPEATABILITY_BLOCKED",
        },
        "verification": {
            "valid": False,
            "requiredLayers": 5,
            "verifiedLayers": 0,
            "layers": layers,
        },
        "errors": errors,
        "errorCount": len(errors),
    }


def validate_phase37(data):
    errors = []

    if not isinstance(data, dict):
        return ["phase37 output is not an object"]

    if data.get("type") != (
        "AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_VERIFY"
    ):
        errors.append("phase37 type mismatch")

    if data.get("mode") != "READ_ONLY":
        errors.append("phase37 mode is not READ_ONLY")

    if data.get("executionAuthorized") is not False:
        errors.append("phase37 executionAuthorized must be false")

    if data.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase37 state is not VERIFIED_READ_ONLY")

    if data.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase37 sourceState is not VERIFIED_READ_ONLY")

    readiness = data.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("phase37 readiness is missing")
    else:
        if readiness.get("ready") is not True:
            errors.append("phase37 readiness.ready is not true")

    verification = data.get("verification")
    if not isinstance(verification, dict):
        errors.append("phase37 verification is missing")
    else:
        if verification.get("valid") is not True:
            errors.append("phase37 verification.valid is not true")
        if verification.get("requiredLayers") != 5:
            errors.append("phase37 requiredLayers must be 5")
        if verification.get("verifiedLayers") != 5:
            errors.append("phase37 verifiedLayers must be 5")

    if data.get("errorCount") != 0:
        errors.append("phase37 errorCount must be zero")

    safety = data.get("safety")
    if not isinstance(safety, dict):
        errors.append("phase37 safety is missing")
    else:
        for key in (
            "postPerformed",
            "walletUsed",
            "signingPerformed",
            "broadcastPerformed",
            "submissionPerformed",
        ):
            if safety.get(key) is not False:
                errors.append(f"phase37 safety.{key} must be false")

    side_effects = data.get("sideEffects")
    if not isinstance(side_effects, dict):
        errors.append("phase37 sideEffects is missing")
    else:
        for key in (
            "network",
            "wallet",
            "signing",
            "broadcast",
            "submission",
        ):
            if side_effects.get(key) is not False:
                errors.append(f"phase37 sideEffects.{key} must be false")

    return errors


def collect_current_layers():
    result = {}
    errors = []

    for name, (relative_path, expected_type) in LAYERS.items():
        path = BASE_DIR / relative_path

        if not path.exists():
            errors.append(f"{name}: artifact missing")
            continue

        data, load_error = load_json(path)
        if load_error:
            errors.append(f"{name}: invalid JSON: {load_error}")
            continue

        actual_type = data.get("type")
        if actual_type != expected_type:
            errors.append(
                f"{name}: type mismatch: "
                f"expected {expected_type}, got {actual_type}"
            )

        try:
            digest = sha256_file(path)
        except Exception as exc:
            errors.append(f"{name}: sha256 failed: {exc}")
            continue

        result[name] = {
            "file": relative_path,
            "type": actual_type,
            "sha256": digest,
        }

    return result, errors


def validate_baseline(baseline):
    errors = []

    if not isinstance(baseline, dict):
        return ["baseline is not an object"]

    if baseline.get("type") != (
        "AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_BASELINE"
    ):
        errors.append("baseline type mismatch")

    if baseline.get("mode") != "READ_ONLY":
        errors.append("baseline mode is not READ_ONLY")

    if baseline.get("executionAuthorized") is not False:
        errors.append("baseline executionAuthorized must be false")

    layers = baseline.get("layers")
    if not isinstance(layers, dict):
        errors.append("baseline layers missing")
        return errors

    for name in LAYERS:
        entry = layers.get(name)
        if not isinstance(entry, dict):
            errors.append(f"baseline {name} missing")
            continue

        expected_file, expected_type = LAYERS[name]

        if entry.get("file") != expected_file:
            errors.append(f"baseline {name} file mismatch")

        if entry.get("type") != expected_type:
            errors.append(f"baseline {name} type mismatch")

        digest = entry.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"baseline {name} sha256 invalid")

    return errors


def compare_layers(baseline, current):
    errors = []
    layers = {}

    baseline_layers = baseline.get("layers", {})

    for name in LAYERS:
        expected = baseline_layers.get(name)
        actual = current.get(name)

        if actual is None:
            layers[name] = "BLOCKED"
            errors.append(f"{name}: current artifact unavailable")
            continue

        if expected.get("file") != actual.get("file"):
            layers[name] = "BLOCKED"
            errors.append(f"{name}: file drift")
            continue

        if expected.get("type") != actual.get("type"):
            layers[name] = "BLOCKED"
            errors.append(f"{name}: type drift")
            continue

        if expected.get("sha256") != actual.get("sha256"):
            layers[name] = "BLOCKED"
            errors.append(f"{name}: sha256 drift")
            continue

        layers[name] = "VERIFIED_READ_ONLY"

    return layers, errors


def build_output(state, source_state, ready, valid, layers, errors):
    return {
        "version": 1,
        "type": TYPE,
        "generatedAt": now(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": {
            "postPerformed": False,
            "walletUsed": False,
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
        },
        "sideEffects": {
            "network": False,
            "filesystemWrite": True,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "readiness": {
            "ready": ready,
            "reason": (
                "CONTINUOUS_READINESS_REPEATABILITY_VERIFIED"
                if ready
                else "CONTINUOUS_READINESS_REPEATABILITY_BLOCKED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 5,
            "verifiedLayers": sum(
                1 for value in layers.values()
                if value == "VERIFIED_READ_ONLY"
            ),
            "layers": layers,
        },
        "sources": {
            name: {
                "file": value["file"],
                "type": value["type"],
                "sha256": value["sha256"],
            }
            for name, value in current_layers.items()
        } if valid else {},
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "networkAccess": False,
            "walletAccess": False,
            "signingAllowed": False,
            "broadcastAllowed": False,
            "submissionAllowed": False,
        },
    }


def main():
    global current_layers

    OBSERVER_DIR.mkdir(parents=True, exist_ok=True)

    errors = []

    phase37, phase37_error = load_json(PHASE37_FILE)

    if phase37_error:
        errors.append(f"phase37 unavailable: {phase37_error}")
    else:
        errors.extend(validate_phase37(phase37))

    if not BASELINE_FILE.exists():
        errors.append("continuous repeatability baseline missing")

    baseline = None
    if BASELINE_FILE.exists():
        baseline, baseline_error = load_json(BASELINE_FILE)
        if baseline_error:
            errors.append(f"baseline unavailable: {baseline_error}")
        else:
            errors.extend(validate_baseline(baseline))

    current_layers, source_errors = collect_current_layers()
    errors.extend(source_errors)

    if errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            {
                name: (
                    "VERIFIED_READ_ONLY"
                    if name in current_layers and not any(
                        error.startswith(f"{name}:")
                        for error in errors
                    )
                    else "BLOCKED"
                )
                for name in LAYERS
            },
            errors,
        )
        OUTPUT_FILE.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("VERIFIED LAYERS: 0/5")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    layers, compare_errors = compare_layers(baseline, current_layers)

    if compare_errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            layers,
            compare_errors,
        )
        OUTPUT_FILE.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print(
            "VERIFIED LAYERS: "
            f"{sum(v == 'VERIFIED_READ_ONLY' for v in layers.values())}/5"
        )
        print(f"ERROR COUNT: {len(compare_errors)}")
        return 1

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        layers,
        [],
    )

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print(
        "VERIFIED LAYERS: "
        f"{sum(v == 'VERIFIED_READ_ONLY' for v in layers.values())}/5"
    )
    print("ERROR COUNT: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
