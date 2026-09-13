#!/usr/bin/env python3

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent

SOURCE = (
    BASE
    / "src"
    / "aacp-phase95-evidence-chain-terminal-finality-gate.py"
)

OBSERVER = BASE / "provider-output" / "aacp-observer"

PHASE94_OUTPUT = (
    OBSERVER
    / "phase94-evidence-snapshot-continuity-terminal-anchor-gate.json"
)

PHASE94_CHECKPOINT = (
    OBSERVER
    / "phase94-evidence-snapshot-continuity-terminal-anchor-gate-checkpoint.json"
)

PHASE94_SOURCE = (
    BASE
    / "src"
    / "aacp-phase94-evidence-snapshot-continuity-terminal-anchor-gate.py"
)


EXPECTED_PHASE94_SOURCE_DIGEST = hashlib.sha256(
    PHASE94_SOURCE.read_bytes()
).hexdigest()


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")


def prepare_source(temp_root):
    source_text = SOURCE.read_text(encoding="utf-8")

    source_text = source_text.replace(
        "BASE = Path(__file__).resolve().parent.parent",
        f'BASE = Path(r"{temp_root}")',
        1,
    )

    source_text = source_text.replace(
        "aee0ed86dd187d33171efe5eaa9389a70fbe348d91ba25f22f29857075bf3950",
        EXPECTED_PHASE94_SOURCE_DIGEST,
        1,
    )

    target = temp_root / "phase95.py"
    target.write_text(
        source_text,
        encoding="utf-8",
    )

    return target


def setup_temp():
    temp_root = Path(
        tempfile.mkdtemp(
            prefix="aacp-phase95-regression-"
        )
    )

    observer = (
        temp_root
        / "provider-output"
        / "aacp-observer"
    )

    source_dir = temp_root / "src"

    observer.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    shutil.copy2(
        PHASE94_OUTPUT,
        observer / PHASE94_OUTPUT.name,
    )

    shutil.copy2(
        PHASE94_CHECKPOINT,
        observer / PHASE94_CHECKPOINT.name,
    )

    shutil.copy2(
        PHASE94_SOURCE,
        source_dir / PHASE94_SOURCE.name,
    )

    prepare_source(temp_root)

    return temp_root


def reset(temp_root):
    observer = (
        temp_root
        / "provider-output"
        / "aacp-observer"
    )

    output_path = temp_root / "phase94-output.json"
    checkpoint_path = temp_root / "phase94-checkpoint.json"

    write(
        output_path,
        load(PHASE94_OUTPUT),
    )

    write(
        checkpoint_path,
        load(PHASE94_CHECKPOINT),
    )

    shutil.copy2(
        output_path,
        observer / PHASE94_OUTPUT.name,
    )

    shutil.copy2(
        checkpoint_path,
        observer / PHASE94_CHECKPOINT.name,
    )

    shutil.copy2(
        PHASE94_SOURCE,
        temp_root
        / "src"
        / PHASE94_SOURCE.name,
    )


def run_gate(temp_root, expected_success):
    proc = subprocess.run(
        ["python3", str(temp_root / "phase95.py")],
        cwd=temp_root,
        text=True,
        capture_output=True,
    )

    output = proc.stdout + proc.stderr

    if expected_success:
        assert proc.returncode == 0, output
        assert "STATE: VERIFIED_READ_ONLY" in output
        assert "READY: True" in output
        assert "VALID: True" in output
        assert "CHECKPOINT: VERIFIED" in output
    else:
        assert proc.returncode != 0, output
        assert "STATE: REJECTED_READ_ONLY" in output

    return output


def mutate_output(temp_root, key, value):
    path = temp_root / "phase94-output.json"

    data = load(path)
    data[key] = value
    write(path, data)

    shutil.copy2(
        path,
        temp_root
        / "provider-output"
        / "aacp-observer"
        / PHASE94_OUTPUT.name,
    )


def mutate_checkpoint(temp_root, key, value):
    path = temp_root / "phase94-checkpoint.json"

    data = load(path)
    data[key] = value
    write(path, data)

    shutil.copy2(
        path,
        temp_root
        / "provider-output"
        / "aacp-observer"
        / PHASE94_CHECKPOINT.name,
    )


def mutate_source(temp_root):
    path = (
        temp_root
        / "src"
        / PHASE94_SOURCE.name
    )

    text = path.read_text(encoding="utf-8")

    path.write_text(
        text + "\n# intentional mutation\n",
        encoding="utf-8",
    )


def main():
    temp_root = setup_temp()

    try:
        # R1 baseline
        reset(temp_root)
        run_gate(temp_root, True)
        print("R1 baseline: PASS")

        # R2 terminal anchor mutation
        reset(temp_root)
        mutate_output(
            temp_root,
            "terminal_anchor_digest",
            "0" * 64,
        )
        run_gate(temp_root, False)
        print("R2 terminal anchor mutation: PASS")

        # R3 Phase94 source anchor mutation
        reset(temp_root)
        mutate_output(
            temp_root,
            "phase94_source_digest",
            "1" * 64,
        )
        run_gate(temp_root, False)
        print("R3 Phase94 source anchor mutation: PASS")

        # R4 checkpoint mutation
        reset(temp_root)
        mutate_checkpoint(
            temp_root,
            "phase",
            999,
        )
        run_gate(temp_root, False)
        print("R4 checkpoint mutation: PASS")

        # R5 state mutation
        reset(temp_root)
        mutate_output(
            temp_root,
            "state",
            "EXECUTABLE",
        )
        run_gate(temp_root, False)
        print("R5 state mutation: PASS")

        # R6 ready mutation
        reset(temp_root)
        mutate_output(
            temp_root,
            "ready",
            False,
        )
        run_gate(temp_root, False)
        print("R6 ready mutation: PASS")

        # R7 valid mutation
        reset(temp_root)
        mutate_output(
            temp_root,
            "valid",
            False,
        )
        run_gate(temp_root, False)
        print("R7 valid mutation: PASS")

        # R8 execution authorization
        reset(temp_root)
        mutate_output(
            temp_root,
            "executionAuthorized",
            True,
        )
        run_gate(temp_root, False)
        print("R8 execution authorization: PASS")

        # R9 network access
        reset(temp_root)
        mutate_output(
            temp_root,
            "networkAccess",
            True,
        )
        run_gate(temp_root, False)
        print("R9 network access: PASS")

        # R10 wallet presence
        reset(temp_root)
        mutate_output(
            temp_root,
            "walletPresent",
            True,
        )
        run_gate(temp_root, False)
        print("R10 wallet presence: PASS")

        # R11 signing
        reset(temp_root)
        mutate_output(
            temp_root,
            "signingEnabled",
            True,
        )
        run_gate(temp_root, False)
        print("R11 signing: PASS")

        # R12 broadcast
        reset(temp_root)
        mutate_output(
            temp_root,
            "broadcastEnabled",
            True,
        )
        run_gate(temp_root, False)
        print("R12 broadcast: PASS")

        # R13 submission
        reset(temp_root)
        mutate_output(
            temp_root,
            "submissionEnabled",
            True,
        )
        run_gate(temp_root, False)
        print("R13 submission: PASS")

        # R14 previous phase
        reset(temp_root)
        mutate_output(
            temp_root,
            "previous_phase",
            88,
        )
        run_gate(temp_root, False)
        print("R14 previous phase: PASS")

        # R15 Phase94 source mutation
        reset(temp_root)
        mutate_source(temp_root)
        run_gate(temp_root, False)
        print("R15 Phase94 source mutation: PASS")

        # R16 restore baseline
        reset(temp_root)
        run_gate(temp_root, True)
        print("R16 restore baseline: PASS")

        print("REGRESSION: 16/16 PASS")

    finally:
        shutil.rmtree(
            temp_root,
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()
