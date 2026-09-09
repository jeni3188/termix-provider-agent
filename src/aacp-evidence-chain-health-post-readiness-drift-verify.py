#!/usr/bin/env python3

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path("provider-output/aacp-observer")

BASELINE_FILE = (
    BASE_DIR
    / "aacp-evidence-chain-health-post-readiness-drift-baseline.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json"
)

LAYERS = {
    "phase31": {
        "file": "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
    },
    "phase32": {
        "file": "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
    },
    "phase33": {
        "file": "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
    },
    "phase34": {
        "file": "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-integrity-attestation.json",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
    },
    "phase35": {
        "file": "provider-output/aacp-observer/"
        "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
    },
}

PHASE36_FILE = (
    BASE_DIR
    / "latest-aacp-evidence-chain-health-final-readiness.json"
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def add_error(errors, code, message):
    errors.append({
        "code": code,
        "message": message,
    })


def safety():
    return {
        "postPerformed": False,
        "walletUsed": False,
        "signingPerformed": False,
        "broadcastPerformed": False,
        "submissionPerformed": False,
    }


def side_effects():
    return {
        "network": False,
        "filesystemWrite": True,
        "wallet": False,
        "signing": False,
        "broadcast": False,
        "submission": False,
    }


def policy():
    return {
        "readOnly": True,
        "failClosed": True,
        "post": "NOT_PERFORMED",
        "wallet": "NOT_USED",
        "signing": "NOT_PERFORMED",
        "broadcast": "NOT_PERFORMED",
        "submission": "NOT_PERFORMED",
    }


def load_json(path, errors, code):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        add_error(errors, code, f"missing file: {path}")
    except (OSError, json.JSONDecodeError) as exc:
        add_error(errors, code, f"cannot read JSON {path}: {exc}")

    return None


def validate_phase36(errors):
    report = load_json(
        PHASE36_FILE,
        errors,
        "PHASE36_MISSING",
    )

    if not isinstance(report, dict):
        return False

    if report.get("type") != "AACP_EVIDENCE_CHAIN_HEALTH_FINAL_READINESS":
        add_error(
            errors,
            "PHASE36_TYPE",
            "Phase 36 type is invalid",
        )

    if report.get("mode") != "READ_ONLY":
        add_error(
            errors,
            "PHASE36_MODE",
            "Phase 36 mode must be READ_ONLY",
        )

    if report.get("state") != "VERIFIED_READ_ONLY":
        add_error(
            errors,
            "PHASE36_STATE",
            "Phase 36 state must be VERIFIED_READ_ONLY",
        )

    if report.get("sourceState") != "VERIFIED_READ_ONLY":
        add_error(
            errors,
            "PHASE36_SOURCE_STATE",
            "Phase 36 sourceState must be VERIFIED_READ_ONLY",
        )

    if report.get("executionAuthorized") is not False:
        add_error(
            errors,
            "PHASE36_EXECUTION",
            "Phase 36 executionAuthorized must be false",
        )

    readiness = report.get("readiness")
    verification = report.get("verification")

    if not isinstance(readiness, dict):
        add_error(errors, "PHASE36_READINESS", "Phase 36 readiness missing")
    elif readiness.get("ready") is not True:
        add_error(
            errors,
            "PHASE36_NOT_READY",
            "Phase 36 readiness.ready must be true",
        )

    if not isinstance(verification, dict):
        add_error(
            errors,
            "PHASE36_VERIFICATION",
            "Phase 36 verification missing",
        )
    else:
        if verification.get("valid") is not True:
            add_error(
                errors,
                "PHASE36_INVALID",
                "Phase 36 verification.valid must be true",
            )

        if verification.get("requiredLayers") != 5:
            add_error(
                errors,
                "PHASE36_REQUIRED_LAYERS",
                "Phase 36 requiredLayers must equal 5",
            )

        if verification.get("verifiedLayers") != 5:
            add_error(
                errors,
                "PHASE36_VERIFIED_LAYERS",
                "Phase 36 verifiedLayers must equal 5",
            )

    if report.get("errorCount") != 0:
        add_error(
            errors,
            "PHASE36_ERRORS",
            "Phase 36 errorCount must equal zero",
        )

    return len(errors) == 0


def collect_sources(errors):
    sources = {}

    for name, spec in LAYERS.items():
        path = Path(spec["file"])

        if not path.is_file():
            add_error(
                errors,
                f"{name.upper()}_MISSING",
                f"{name} source artifact missing: {path}",
            )
            continue

        report = load_json(
            path,
            errors,
            f"{name.upper()}_INVALID_JSON",
        )

        if not isinstance(report, dict):
            continue

        if report.get("type") != spec["type"]:
            add_error(
                errors,
                f"{name.upper()}_TYPE",
                f"{name} artifact type mismatch",
            )

        try:
            digest = sha256_file(path)
        except OSError as exc:
            add_error(
                errors,
                f"{name.upper()}_HASH",
                f"{name} SHA-256 failed: {exc}",
            )
            continue

        sources[name] = {
            "file": str(path),
            "exists": True,
            "sha256": digest,
            "type": spec["type"],
        }

    return sources


def build_baseline(sources):
    return {
        "version": "1.0.0",
        "type": (
            "AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_BASELINE"
        ),
        "generatedAt": now(),
        "mode": "READ_ONLY",
        "executionAuthorized": False,
        "layers": sources,
        "policy": policy(),
    }


def compare_baseline(baseline, sources, errors):
    if not isinstance(baseline, dict):
        add_error(
            errors,
            "BASELINE_INVALID",
            "baseline must be a JSON object",
        )
        return

    if baseline.get("type") != (
        "AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_BASELINE"
    ):
        add_error(
            errors,
            "BASELINE_TYPE",
            "baseline type is invalid",
        )

    if baseline.get("mode") != "READ_ONLY":
        add_error(
            errors,
            "BASELINE_MODE",
            "baseline mode must be READ_ONLY",
        )

    if baseline.get("executionAuthorized") is not False:
        add_error(
            errors,
            "BASELINE_EXECUTION",
            "baseline executionAuthorized must be false",
        )

    baseline_layers = baseline.get("layers")

    if not isinstance(baseline_layers, dict):
        add_error(
            errors,
            "BASELINE_LAYERS",
            "baseline layers object missing",
        )
        return

    for name in LAYERS:
        expected = baseline_layers.get(name)
        actual = sources.get(name)

        if not isinstance(expected, dict):
            add_error(
                errors,
                f"{name.upper()}_BASELINE",
                f"{name} baseline entry missing",
            )
            continue

        if not isinstance(actual, dict):
            add_error(
                errors,
                f"{name.upper()}_CURRENT",
                f"{name} current source missing",
            )
            continue

        if expected.get("sha256") != actual.get("sha256"):
            add_error(
                errors,
                f"{name.upper()}_DRIFT",
                f"{name} SHA-256 drift detected",
            )

        if expected.get("type") != actual.get("type"):
            add_error(
                errors,
                f"{name.upper()}_TYPE_DRIFT",
                f"{name} type drift detected",
            )

        if expected.get("file") != actual.get("file"):
            add_error(
                errors,
                f"{name.upper()}_PATH_DRIFT",
                f"{name} path drift detected",
            )


def build_report():
    errors = []

    phase36_valid = validate_phase36(errors)
    sources = collect_sources(errors)

    baseline_exists = BASELINE_FILE.is_file()
    baseline_created = False

    if not phase36_valid:
        state = "BLOCKED"
        source_state = "BLOCKED"
    elif not baseline_exists:
        if len(sources) != len(LAYERS):
            state = "BLOCKED"
            source_state = "BLOCKED"
        else:
            baseline = build_baseline(sources)

            BASE_DIR.mkdir(parents=True, exist_ok=True)

            with open(
                BASELINE_FILE,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    baseline,
                    f,
                    indent=2,
                    sort_keys=False,
                )
                f.write("\n")

            baseline_created = True

            state = "BASELINE_ESTABLISHED"
            source_state = "BASELINE_ESTABLISHED"
    else:
        baseline = load_json(
            BASELINE_FILE,
            errors,
            "BASELINE_READ",
        )

        compare_baseline(
            baseline,
            sources,
            errors,
        )

        if errors:
            state = "BLOCKED"
            source_state = "BLOCKED"
        else:
            state = "VERIFIED_READ_ONLY"
            source_state = "VERIFIED_READ_ONLY"

    if errors:
        ready = False
        valid = False
    elif baseline_created:
        ready = False
        valid = True
    else:
        ready = True
        valid = True

    reason = (
        "BASELINE_ESTABLISHED"
        if baseline_created
        else (
            "ALL_SOURCES_MATCH_BASELINE"
            if valid
            else "DRIFT_OR_INTEGRITY_FAILURE"
        )
    )

    report = {
        "version": "1.0.0",
        "type": (
            "AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_VERIFY"
        ),
        "generatedAt": now(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": safety(),
        "sideEffects": side_effects(),
        "readiness": {
            "ready": ready,
            "reason": reason,
        },
        "verification": {
            "valid": valid,
            "baselineExists": baseline_exists or baseline_created,
            "baselineCreated": baseline_created,
            "requiredLayers": 5,
            "verifiedLayers": (
                5
                if valid and not baseline_created and not errors
                else 0
            ),
            "layers": {
                name: (
                    "VERIFIED_READ_ONLY"
                    if name in sources
                    and not baseline_created
                    and not errors
                    else "BASELINE_ESTABLISHED"
                    if baseline_created and name in sources
                    else "BLOCKED"
                )
                for name in LAYERS
            },
        },
        "sources": sources,
        "errors": errors,
        "errorCount": len(errors),
        "policy": policy(),
    }

    BASE_DIR.mkdir(parents=True, exist_ok=True)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            sort_keys=False,
        )
        f.write("\n")

    return report


def main():
    report = build_report()

    print(f"STATE: {report['state']}")
    print(f"SOURCE STATE: {report['sourceState']}")
    print(f"READY: {report['readiness']['ready']}")
    print(f"VALID: {report['verification']['valid']}")
    print(
        "VERIFIED LAYERS: "
        f"{report['verification']['verifiedLayers']}/5"
    )
    print(f"ERROR COUNT: {report['errorCount']}")

    for error in report["errors"]:
        print(
            f"ERROR {error['code']}: "
            f"{error['message']}"
        )

    return 0 if report["verification"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
