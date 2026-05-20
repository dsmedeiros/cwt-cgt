"""Print the external dataset candidates listed in the Phase-230 manifest.

Usage::

    cd cwt-sim
    python scripts/cgt/externalization_inventory.py

The script resolves the manifest path relative to this file:
    scripts/cgt/externalization_inventory.py
      parents[0] = scripts/cgt/
      parents[1] = scripts/
      parents[2] = cwt-sim/
    -> cwt-sim/cgt_benchmarks/externalization/CWT-CGT_Phase_230_External_Metadata_Manifest.json
"""
from __future__ import annotations

from pathlib import Path

from cwt.cgt.external_adapters import load_manifest


def main() -> None:
    """Load the manifest and print each candidate with its priority and domain."""
    base = Path(__file__).resolve().parents[2]
    manifest_path = (
        base
        / "cgt_benchmarks"
        / "externalization"
        / "CWT-CGT_Phase_230_External_Metadata_Manifest.json"
    )
    data = load_manifest(manifest_path)
    print("External candidates:")
    for item in data.get("candidates", []):
        print(f"- {item['name']} [{item['priority']}] :: {item['domain']}")


if __name__ == "__main__":
    main()
