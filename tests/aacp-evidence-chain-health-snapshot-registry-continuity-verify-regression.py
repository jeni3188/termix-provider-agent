#!/usr/bin/env python3

import copy
import importlib.util
import json
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE = (
    BASE_DIR
    / "src"
    / "aacp-evidence-chain-health-snapshot-registry-continuity-verify.py"
)

spec = importlib.util.spec_from_file_location("phase42", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def expect(name, condition):
    if not condition:
        raise AssertionError(f"FAIL: {name}")
    print(f"PASS: {name}")


def run():
    original_checkpoint = (
        module.CHECKPOINT_FILE.read_text()
        if module.CHECKPOINT_FILE.exists()
        else None
    )

    original_output = (
        module.OUTPUT_FILE.read_text()
        if module.OUTPUT_FILE.exists()
        else None
    )

    phase41_path = module.PHASE41_FILE
    original_phase41 = phase41_path.read_text()

    try:
        # Establish a clean Phase42 checkpoint.
        module.CHECKPOINT_FILE.unlink(missing_ok=True)
        module.OUTPUT_FILE.unlink(missing_ok=True)

        # 1. First run establishes checkpoint.
        result, errors = module.verify_continuity()

        expect(
            "first run establishes checkpoint",
            not errors
            and result["state"] == "CHECKPOINT_ESTABLISHED"
            and result["ready"] is False
            and result["valid"] is True
            and result["verifiedLayers"] == 0,
        )

        # Create the checkpoint exactly as main() does.
        phase41 = module.load_json(module.PHASE41_FILE)
        module.write_checkpoint(phase41)

        # 2. Second run verifies continuity.
        result, errors = module.verify_continuity()

        expect(
            "second run verifies continuity",
            not errors
            and result["state"] == "VERIFIED_READ_ONLY"
            and result["ready"] is True
            and result["valid"] is True
            and result["verifiedLayers"] == 9,
        )

        # 3. Semantic digest is deterministic.
        digest1 = module.semantic_digest(phase41)
        digest2 = module.semantic_digest(phase41)

        expect(
            "semantic digest is deterministic",
            digest1 == digest2
            and len(digest1) == 64,
        )

        # 4. generatedAt-only change must not cause drift.
        mutated = copy.deepcopy(phase41)
        mutated["generatedAt"] = "2099-01-01T00:00:00+00:00"
        phase41_path.write_text(
            json.dumps(mutated, indent=2, ensure_ascii=False) + "\n"
        )

        result, errors = module.verify_continuity()

        expect(
            "generatedAt-only change is ignored",
            not errors
            and result["state"] == "VERIFIED_READ_ONLY"
            and result["valid"] is True,
        )

        phase41_path.write_text(original_phase41)

        # 5. Semantic state drift is blocked.
        mutated = copy.deepcopy(phase41)
        mutated["state"] = "BLOCKED"
        phase41_path.write_text(
            json.dumps(mutated, indent=2, ensure_ascii=False) + "\n"
        )

        result, errors = module.verify_continuity()

        expect(
            "semantic state drift is blocked",
            "phase41 artifact validation failed" in errors,
        )

        phase41_path.write_text(original_phase41)

        # 6. Registry digest drift is blocked.
        mutated = copy.deepcopy(phase41)
        mutated["verification"]["registryDigest"] = "0" * 64
        phase41_path.write_text(
            json.dumps(mutated, indent=2, ensure_ascii=False) + "\n"
        )

        result, errors = module.verify_continuity()

        expect(
            "registry digest drift is blocked",
            "semantic digest drift detected" in errors
            or "semantic projection drift detected" in errors,
        )

        phase41_path.write_text(original_phase41)

        # 7. Execution authorization violation is blocked.
        mutated = copy.deepcopy(phase41)
        mutated["executionAuthorized"] = True
        phase41_path.write_text(
            json.dumps(mutated, indent=2, ensure_ascii=False) + "\n"
        )

        result, errors = module.verify_continuity()

        expect(
            "execution authorization violation is blocked",
            "phase41 artifact validation failed" in errors,
        )

        phase41_path.write_text(original_phase41)

        # 8. Wallet safety violation is blocked.
        mutated = copy.deepcopy(phase41)
        mutated["safety"]["walletUsed"] = True
        phase41_path.write_text(
            json.dumps(mutated, indent=2, ensure_ascii=False) + "\n"
        )

        result, errors = module.verify_continuity()

        expect(
            "wallet safety violation is blocked",
            "phase41 artifact validation failed" in errors,
        )

        phase41_path.write_text(original_phase41)

        # 9. Error count violation is blocked.
        mutated = copy.deepcopy(phase41)
        mutated["errorCount"] = 1
        phase41_path.write_text(
            json.dumps(mutated, indent=2, ensure_ascii=False) + "\n"
        )

        result, errors = module.verify_continuity()

        expect(
            "phase41 error count violation is blocked",
            "phase41 artifact validation failed" in errors,
        )

        phase41_path.write_text(original_phase41)

        # 10. Corrupted Phase41 JSON is blocked.
        phase41_path.write_text("{broken-json")

        result, errors = module.verify_continuity()

        expect(
            "corrupted phase41 JSON is blocked",
            "phase41 artifact is invalid JSON" in errors,
        )

        phase41_path.write_text(original_phase41)

        # 11. Corrupted checkpoint is blocked.
        module.CHECKPOINT_FILE.write_text("{broken-checkpoint")

        result, errors = module.verify_continuity()

        expect(
            "corrupted checkpoint is blocked",
            "continuity checkpoint is invalid" in errors,
        )

        # 12. Checkpoint semantic projection tampering is blocked.
        phase41 = module.load_json(module.PHASE41_FILE)
        module.write_checkpoint(phase41)

        checkpoint = module.load_json(module.CHECKPOINT_FILE)
        checkpoint["semanticProjection"]["state"] = "BLOCKED"

        module.CHECKPOINT_FILE.write_text(
            json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n"
        )

        result, errors = module.verify_continuity()

        expect(
            "checkpoint projection tampering is blocked",
            "continuity checkpoint is invalid" in errors
            or "semantic digest drift detected" in errors
            or "semantic projection drift detected" in errors,
        )

        # 13. Missing Phase41 artifact is blocked.
        module.CHECKPOINT_FILE.unlink(missing_ok=True)
        phase41_path.unlink()

        result, errors = module.verify_continuity()

        expect(
            "missing phase41 artifact is blocked",
            "phase41 artifact is invalid JSON" in errors,
        )

        # Restore Phase41 before final deterministic check.
        phase41_path.write_text(original_phase41)

        # 14. Full continuity remains valid after restoration.
        module.CHECKPOINT_FILE.unlink(missing_ok=True)
        phase41 = module.load_json(module.PHASE41_FILE)
        module.write_checkpoint(phase41)

        result, errors = module.verify_continuity()

        expect(
            "restored continuity verifies 9/9",
            not errors
            and result["state"] == "VERIFIED_READ_ONLY"
            and result["ready"] is True
            and result["valid"] is True
            and result["verifiedLayers"] == 9,
        )

        print("RESULT: 14/14 PASSED")

    finally:
        phase41_path.write_text(original_phase41)

        if original_checkpoint is None:
            module.CHECKPOINT_FILE.unlink(missing_ok=True)
        else:
            module.CHECKPOINT_FILE.write_text(original_checkpoint)

        if original_output is None:
            module.OUTPUT_FILE.unlink(missing_ok=True)
        else:
            module.OUTPUT_FILE.write_text(original_output)


if __name__ == "__main__":
    run()
