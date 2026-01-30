"""Script to check and process SPDX license data."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPDX_JSON = ROOT / "resources" / "spdx_license_list.json"
OUT_SCHEMA = ROOT / "schemas" / "spdx_licenses.schema.json"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpdxLicense:
    """Representation of an SPDX license."""

    license_id: str
    name: str
    is_osi_approved: bool
    is_fsf_libre: bool
    is_deprecated: bool


def load_spdx_license_list(path: Path) -> dict[str, SpdxLicense]:
    """Load SPDX license list from JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    licenses: list[dict[str, any]] = raw["licenses"]
    by_id: dict[str, SpdxLicense] = {}
    for license_ in licenses:
        license_id: str = license_["licenseId"]
        name: str = license_["name"]
        by_id[license_id] = SpdxLicense(
            license_id=license_id,
            name=name,
            is_osi_approved=bool(license_.get("isOsiApproved", False)),
            is_fsf_libre=bool(license_.get("isFsfLibre", False)),
            is_deprecated=bool(license_.get("isDeprecatedLicenseId", False)),
        )
    return by_id


SPDX_LICENSES: dict[str, SpdxLicense] = load_spdx_license_list(SPDX_JSON)


def is_foss(license_id: str) -> bool:
    """Determine whether a license list can be treated as open-source/FOSS.

    if license is in SPDX_LICENSES and is either OSI-approved or FSF-libre,
    it is considered open source.
    """
    if license_ := SPDX_LICENSES.get(license_id):
        return license_.is_osi_approved or license_.is_fsf_libre
    return False


def generate_enum_schema(by_id: dict[str, SpdxLicense]) -> dict[str, Any]:
    """Generate JSON schema with enum of SPDX license IDs."""
    enum_ids = sorted(by_id.keys())

    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "spdx_licenses.schema.json",
        "title": "SPDX License IDs",
        "description": "Generated SPDX licenseId enum.",
        "type": "string",
        "enum": enum_ids,
    }
    return schema


def main() -> None:
    """Main entry point for the script."""
    schema = generate_enum_schema(SPDX_LICENSES)

    OUT_SCHEMA.parent.mkdir(parents=True, exist_ok=True)
    OUT_SCHEMA.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[check_spdx] OK: loaded {len(SPDX_LICENSES)} SPDX license IDs")
    print(f"[check_spdx] OK: wrote enum schema -> {OUT_SCHEMA}")


if __name__ == "__main__":
    main()
