#!/usr/bin/env python3

import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE = (
    BASE_DIR
    / "src"
    / "aacp-evidence-chain-health-snapshot-registry-verifier.py"
)

spec = importlib.util.spec_from_file_location("phase41", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def load_registry():
    return json.loads(module.REGISTRY_FILE.read_text())


def write_registry(data):
    module.REGISTRY_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )


def expect(name, condition):
    if not condition:
        raise AssertionError(f"FAIL: {name}")
    print(f"PASS: {name}")


original = load_registry()

try:
    # 1. Normal verification
    result, errors = module.verify_registry()
    expect(
        "normal registry verifies 9/9",
        not errors
        and result["verifiedLayers"] == 9
        and result["requiredLayers"] == 9,
    )

    # 2. Registry digest mismatch
    mutated = copy.deepcopy(original)
    mutated["registry"]["registryDigest"] = "0" * 64
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "registry digest mismatch is blocked",
        "registry digest mismatch" in errors,
    )

    # 3. Missing registry payload
    mutated = copy.deepcopy(original)
    mutated.pop("registry", None)
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "missing registry payload is blocked",
        "registry payload is invalid" in errors,
    )

    # 4. Corrupted registry JSON
    module.REGISTRY_FILE.write_text("{broken-json")
    result, errors = module.verify_registry()
    expect(
        "corrupted registry JSON is blocked",
        "registry artifact is invalid JSON" in errors,
    )

    # 5. Wrong registry type
    mutated = copy.deepcopy(original)
    mutated["registry"]["type"] = "WRONG_TYPE"
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "registry type mismatch is blocked",
        "registry type mismatch" in errors,
    )

    # 6. Wrong layer count
    mutated = copy.deepcopy(original)
    mutated["registry"]["layerCount"] = 8
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "registry layerCount mismatch is blocked",
        "registry layerCount mismatch" in errors,
    )

    # 7. Missing Phase31 registry entry
    mutated = copy.deepcopy(original)
    mutated["registry"]["layers"].pop("phase31")
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "missing phase31 entry is blocked",
        "phase31 registry entry missing" in errors,
    )

    # 8. Phase39 SHA mismatch
    mutated = copy.deepcopy(original)
    mutated["registry"]["layers"]["phase39"]["sha256"] = "0" * 64
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "phase39 sha256 mismatch is blocked",
        "phase39 sha256 mismatch" in errors,
    )

    # 9. Phase36 path mismatch
    mutated = copy.deepcopy(original)
    mutated["registry"]["layers"]["phase36"]["path"] = "wrong/path.json"
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "phase36 path mismatch is blocked",
        "phase36 path mismatch" in errors,
    )

    # 10. Phase35 type mismatch
    mutated = copy.deepcopy(original)
    mutated["registry"]["layers"]["phase35"]["type"] = "WRONG_TYPE"
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "phase35 type mismatch is blocked",
        "phase35 type mismatch" in errors,
    )

    # 11. Registry envelope execution authorization violation
    mutated = copy.deepcopy(original)
    mutated["executionAuthorized"] = True
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "registry execution authorization violation is blocked",
        "registry execution authorization violation" in errors,
    )

    # 12. Registry envelope wallet safety violation
    mutated = copy.deepcopy(original)
    mutated["safety"]["walletUsed"] = True
    write_registry(mutated)
    result, errors = module.verify_registry()
    expect(
        "registry wallet safety violation is blocked",
        "registry safety violation" in errors,
    )

    # 13. Phase31 state violation
    mutated = copy.deepcopy(original)

    phase31_path = (
        module.OBSERVER_DIR
        / module.PHASE_FILES[31]
    )

    original_phase31 = json.loads(phase31_path.read_text())

    broken_phase31 = copy.deepcopy(original_phase31)
    broken_phase31["state"] = "VERIFIED_READ_ONLY"
    phase31_path.write_text(
        json.dumps(
            broken_phase31,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    result, errors = module.verify_registry()

    expect(
        "phase31 semantic state violation is blocked",
        "phase31 artifact validation failed" in errors,
    )

    phase31_path.write_text(
        json.dumps(
            original_phase31,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    # 14. Deterministic registry digest
    restored = load_registry()
    core = {
        "version": restored["registry"]["version"],
        "type": restored["registry"]["type"],
        "mode": restored["registry"]["mode"],
        "layers": restored["registry"]["layers"],
        "layerCount": restored["registry"]["layerCount"],
    }

    digest1 = hashlib.sha256(
        canonical(core).encode("utf-8")
    ).hexdigest()

    digest2 = hashlib.sha256(
        canonical(core).encode("utf-8")
    ).hexdigest()

    expect(
        "registry digest is deterministic",
        digest1 == digest2
        and digest1 == restored["registry"]["registryDigest"],
    )

finally:
    write_registry(original)

    # Restore Phase31 exactly as it was if the test mutated it.
    phase31_path = (
        module.OBSERVER_DIR
        / module.PHASE_FILES[31]
    )

    # Registry restoration is always performed.
    # Phase31 is restored from git to avoid leaving test mutations.
    import subprocess

    subprocess.run(
        [
            "git",
            "checkout",
            "--",
            str(
                phase31_path.relative_to(BASE_DIR)
            ),
        ],
        cwd=BASE_DIR,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

print("RESULT: 14/14 PASSED")
