#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OBSERVER = BASE_DIR / "provider-output" / "aacp-observer"

SOURCE = (
    BASE_DIR
    / "src"
    / "aacp-evidence-chain-health-semantic-checkpoint-verify.py"
)

PHASE38 = (
    OBSERVER
    / "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json"
)

CHECKPOINT = (
    OBSERVER
    / "aacp-evidence-chain-health-semantic-checkpoint.json"
)

OUTPUT = (
    OBSERVER
    / "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json"
)


def run():
    return subprocess.run(
        ["python", str(SOURCE)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
    )


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def assert_blocked(label):
    result = run()
    assert result.returncode != 0, label

    output = load(OUTPUT)

    assert output["state"] == "BLOCKED", label
    assert output["verification"]["valid"] is False, label

    print(f"PASS: {label}")


def main():
    original_phase38 = PHASE38.read_text(encoding="utf-8")

    checkpoint_exists = CHECKPOINT.exists()
    original_checkpoint = (
        CHECKPOINT.read_text(encoding="utf-8")
        if checkpoint_exists
        else None
    )

    try:
        if CHECKPOINT.exists():
            CHECKPOINT.unlink()

        result = run()
        assert result.returncode == 0

        output = load(OUTPUT)
        assert output["state"] == "CHECKPOINT_ESTABLISHED"
        assert output["verification"]["valid"] is True
        print("PASS: first run establishes semantic checkpoint")

        result = run()
        assert result.returncode == 0

        output = load(OUTPUT)
        assert output["state"] == "VERIFIED_READ_ONLY"
        assert output["readiness"]["ready"] is True
        assert output["verification"]["valid"] is True
        print("PASS: unchanged semantic state verifies")

        phase38 = load(PHASE38)
        phase38["readiness"]["reason"] = "SEMANTIC_REGRESSION_DRIFT"
        save(PHASE38, phase38)

        assert_blocked("readiness semantic drift is blocked")
        PHASE38.write_text(original_phase38, encoding="utf-8")

        phase38 = load(PHASE38)
        phase38["verification"]["verifiedLayers"] = 4
        save(PHASE38, phase38)

        assert_blocked("verification layer drift is blocked")
        PHASE38.write_text(original_phase38, encoding="utf-8")

        phase38 = load(PHASE38)
        phase38["executionAuthorized"] = True
        save(PHASE38, phase38)

        assert_blocked("execution authorization drift is blocked")
        PHASE38.write_text(original_phase38, encoding="utf-8")

        phase38 = load(PHASE38)
        phase38["safety"]["signingPerformed"] = True
        save(PHASE38, phase38)

        assert_blocked("signing safety drift is blocked")
        PHASE38.write_text(original_phase38, encoding="utf-8")

        checkpoint = load(CHECKPOINT)
        checkpoint["type"] = "CORRUPTED_CHECKPOINT"
        save(CHECKPOINT, checkpoint)

        assert_blocked("checkpoint type corruption is blocked")
        CHECKPOINT.write_text(original_checkpoint, encoding="utf-8")

        checkpoint = load(CHECKPOINT)
        checkpoint["semanticDigest"] = "0" * 64
        save(CHECKPOINT, checkpoint)

        assert_blocked("checkpoint digest drift is blocked")
        CHECKPOINT.write_text(original_checkpoint, encoding="utf-8")

        checkpoint = load(CHECKPOINT)
        checkpoint["executionAuthorized"] = True
        save(CHECKPOINT, checkpoint)

        assert_blocked("checkpoint execution authorization violation is blocked")
        CHECKPOINT.write_text(original_checkpoint, encoding="utf-8")

        checkpoint = load(CHECKPOINT)
        checkpoint["semanticProjection"]["readiness"]["ready"] = False
        save(CHECKPOINT, checkpoint)

        assert_blocked("checkpoint semantic projection drift is blocked")
        CHECKPOINT.write_text(original_checkpoint, encoding="utf-8")

        phase38 = load(PHASE38)
        phase38["generatedAt"] = "2099-01-01T00:00:00+00:00"
        save(PHASE38, phase38)

        result = run()
        assert result.returncode == 0
        output = load(OUTPUT)
        assert output["state"] == "VERIFIED_READ_ONLY"
        assert output["verification"]["valid"] is True
        print("PASS: generatedAt-only change is ignored")

        print("\nRESULT: 11/11 PASSED")

    finally:
        PHASE38.write_text(original_phase38, encoding="utf-8")

        if original_checkpoint is None:
            if CHECKPOINT.exists():
                CHECKPOINT.unlink()
        else:
            CHECKPOINT.write_text(original_checkpoint, encoding="utf-8")


if __name__ == "__main__":
    main()
