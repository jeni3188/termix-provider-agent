#!/usr/bin/env python3

import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "src" / "aacp-phase89-evidence-artifact-integrity-continuity-gate.py"
)

REAL_OUT = ROOT / "provider-output" / "aacp-observer"

OUTPUT_NAME = "phase88-evidence-artifact-integrity-gate.json"
CHECKPOINT_NAME = "phase88-evidence-artifact-integrity-gate-checkpoint.json"


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_gate_module():
    spec = importlib.util.spec_from_file_location(
        "aacp_phase89_gate_test",
        SOURCE,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def run_case(output_mutator=None, checkpoint_mutator=None):
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        temp_out = temp_root / "provider-output" / "aacp-observer"
        temp_out.mkdir(parents=True)

        output = json.loads(
            (REAL_OUT / OUTPUT_NAME).read_text()
        )

        checkpoint = json.loads(
            (REAL_OUT / CHECKPOINT_NAME).read_text()
        )

        if output_mutator:
            output_mutator(output)

        if checkpoint_mutator:
            checkpoint_mutator(checkpoint)

        (temp_out / OUTPUT_NAME).write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n"
        )

        (temp_out / CHECKPOINT_NAME).write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True) + "\n"
        )

        gate = load_gate_module()

        # Redirect only test artifact locations.
        # Production source bytes remain untouched.
        gate.OUT = temp_out
        gate.PHASE88_OUTPUT = temp_out / OUTPUT_NAME
        gate.PHASE88_CHECKPOINT = temp_out / CHECKPOINT_NAME

        # Keep the real Phase88 source and verify its real SHA256.
        gate.PHASE88_SOURCE = (
            ROOT / "src" / "aacp-phase88-evidence-artifact-integrity-gate.py"
        )
        gate.EXPECTED_PHASE88_SOURCE_DIGEST = sha256_file(
            gate.PHASE88_SOURCE
        )

        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):
                gate.main()

            return 0, stdout.getvalue()

        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            return code, stdout.getvalue()


def must(condition, message):
    if not condition:
        raise AssertionError(message)


baseline = run_case()
must(baseline[0] == 0, "baseline failed")
print("R1 baseline: PASS")


r2 = run_case(
    output_mutator=lambda x: x.__setitem__(
        "phase87_continuity_digest",
        "f" * 64,
    )
)
must(r2[0] != 0, "continuity mutation accepted")
print("R2 continuity mutation: PASS")


r3 = run_case(
    output_mutator=lambda x: x.__setitem__(
        "artifact_integrity_digest",
        "f" * 64,
    )
)
must(r3[0] != 0, "artifact digest mutation accepted")
print("R3 artifact digest mutation: PASS")


r4 = run_case(
    output_mutator=lambda x: x.__setitem__(
        "executionAuthorized",
        True,
    )
)
must(r4[0] != 0, "execution authorization mutation accepted")
print("R4 execution authorization mutation: PASS")


r5 = run_case(
    output_mutator=lambda x: x.__setitem__(
        "networkAccess",
        True,
    )
)
must(r5[0] != 0, "network mutation accepted")
print("R5 network mutation: PASS")


r6 = run_case(
    output_mutator=lambda x: x.__setitem__(
        "walletPresent",
        True,
    )
)
must(r6[0] != 0, "wallet mutation accepted")
print("R6 wallet mutation: PASS")


r7 = run_case(
    output_mutator=lambda x: x.__setitem__(
        "state",
        "EXECUTABLE",
    )
)
must(r7[0] != 0, "state mutation accepted")
print("R7 state mutation: PASS")


r8 = run_case(
    checkpoint_mutator=lambda x: x.__setitem__(
        "artifact_integrity_digest",
        "f" * 64,
    )
)
must(r8[0] != 0, "checkpoint mutation accepted")
print("R8 checkpoint mutation: PASS")


r9 = run_case(
    output_mutator=lambda x: x.__setitem__(
        "phase",
        999,
    )
)
must(r9[0] != 0, "phase mutation accepted")
print("R9 phase mutation: PASS")


r10 = run_case(
    checkpoint_mutator=lambda x: x.__setitem__(
        "previous_phase",
        999,
    )
)
must(r10[0] != 0, "previous phase mutation accepted")
print("R10 previous phase mutation: PASS")


baseline2 = run_case()
must(baseline2[0] == 0, "restore baseline failed")
print("R11 restore baseline: PASS")


print("REGRESSION: 11/11 PASS")
