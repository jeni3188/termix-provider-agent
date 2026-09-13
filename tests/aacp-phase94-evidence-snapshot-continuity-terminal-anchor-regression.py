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
    / "aacp-phase94-evidence-snapshot-continuity-terminal-anchor-gate.py"
)

OBSERVER = BASE / "provider-output" / "aacp-observer"

PHASE93_OUTPUT = (
    OBSERVER
    / "phase93-terminal-evidence-snapshot-integrity-gate.json"
)

PHASE93_CHECKPOINT = (
    OBSERVER
    / "phase93-terminal-evidence-snapshot-integrity-gate-checkpoint.json"
)

PHASE93_SOURCE = (
    BASE
    / "src"
    / "aacp-phase93-terminal-evidence-snapshot-integrity-gate.py"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


EXPECTED_PHASE93_SOURCE_DIGEST = sha256_file(PHASE93_SOURCE)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def prepare_source(temp_root):
    source_text = SOURCE.read_text(encoding="utf-8")

    source_text = source_text.replace(
        'BASE = Path(__file__).resolve().parent.parent',
        f'BASE = Path(r"{temp_root}")',
        1,
    )

    source_text = source_text.replace(
        '067dc6ba5c3e219c28594290f3ab233adb2ecfcd2292c8ec0428436bef25d5cd',
        EXPECTED_PHASE93_SOURCE_DIGEST,
        1,
    )

    target = temp_root / "phase94.py"
    target.write_text(source_text, encoding="utf-8")
    return target


def run_gate(temp_root, expected_success):
    proc = subprocess.run(
        ["python3", str(temp_root / "phase94.py")],
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


def reset(temp_root):
    observer = temp_root / "provider-output" / "aacp-observer"

    output_path = temp_root / "phase93-output.json"
    checkpoint_path = temp_root / "phase93-checkpoint.json"

    write(output_path, load(PHASE93_OUTPUT))
    write(checkpoint_path, load(PHASE93_CHECKPOINT))

    shutil.copy2(
        output_path,
        observer / PHASE93_OUTPUT.name,
    )
    shutil.copy2(
        checkpoint_path,
        observer / PHASE93_CHECKPOINT.name,
    )

    shutil.copy2(
        PHASE93_SOURCE,
        temp_root / "src" / PHASE93_SOURCE.name,
    )


def setup_temp():
    temp_root = Path(tempfile.mkdtemp(prefix="aacp-phase94-regression-"))

    observer = temp_root / "provider-output" / "aacp-observer"
    source_dir = temp_root / "src"

    observer.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    shutil.copy2(PHASE93_OUTPUT, observer / PHASE93_OUTPUT.name)
    shutil.copy2(PHASE93_CHECKPOINT, observer / PHASE93_CHECKPOINT.name)
    shutil.copy2(PHASE93_SOURCE, source_dir / PHASE93_SOURCE.name)

    # Phase94 source expects the production filenames.
    prepare_source(temp_root)

    return temp_root


def mutate_json(path, key, value):
    data = load(path)
    data[key] = value
    write(path, data)


def main():
    temp_root = setup_temp()

    try:
        # R1 baseline
        reset(temp_root)
        run_gate(temp_root, True)
        print("R1 baseline: PASS")

        # R2 source digest mutation
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "terminal_snapshot_digest",
            "0" * 64,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R2 terminal snapshot mutation: PASS")

        # R3 checkpoint mutation
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-checkpoint.json",
            "phase",
            999,
        )
        shutil.copy2(
            temp_root / "phase93-checkpoint.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_CHECKPOINT.name,
        )
        run_gate(temp_root, False)
        print("R3 checkpoint mutation: PASS")

        # R4 state mutation
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "state",
            "EXECUTABLE",
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R4 state mutation: PASS")

        # R5 ready mutation
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "ready",
            False,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R5 ready mutation: PASS")

        # R6 valid mutation
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "valid",
            False,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R6 valid mutation: PASS")

        # R7 execution authorization
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "executionAuthorized",
            True,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R7 execution authorization: PASS")

        # R8 network access
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "networkAccess",
            True,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R8 network access: PASS")

        # R9 wallet presence
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "walletPresent",
            True,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R9 wallet presence: PASS")

        # R10 signing
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "signingEnabled",
            True,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R10 signing: PASS")

        # R11 broadcast
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "broadcastEnabled",
            True,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R11 broadcast: PASS")

        # R12 submission
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "submissionEnabled",
            True,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R12 submission: PASS")

        # R13 previous phase
        reset(temp_root)
        mutate_json(
            temp_root / "phase93-output.json",
            "previous_phase",
            90,
        )
        shutil.copy2(
            temp_root / "phase93-output.json",
            temp_root
            / "provider-output"
            / "aacp-observer"
            / PHASE93_OUTPUT.name,
        )
        run_gate(temp_root, False)
        print("R13 previous phase: PASS")

        # R14 source mutation
        reset(temp_root)
        mutated_source = (
            temp_root
            / "src"
            / PHASE93_SOURCE.name
        )
        source_text = mutated_source.read_text(encoding="utf-8")
        mutated_source.write_text(
            source_text + "\n# mutation\n",
            encoding="utf-8",
        )
        run_gate(temp_root, False)
        print("R14 Phase93 source mutation: PASS")

        # R15 restore baseline
        reset(temp_root)
        shutil.copy2(
            PHASE93_SOURCE,
            temp_root / "src" / PHASE93_SOURCE.name,
        )
        run_gate(temp_root, True)
        print("R15 restore baseline: PASS")

        print("REGRESSION: 15/15 PASS")

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
