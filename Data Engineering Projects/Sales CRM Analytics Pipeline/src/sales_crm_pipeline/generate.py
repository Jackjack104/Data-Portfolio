from __future__ import annotations

import csv
import json
import random
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sales_crm_pipeline.normalize import normalize_company_name

COMPANY_PREFIXES = [
    "Atlantic",
    "Bluewater",
    "Cypress",
    "Evergreen",
    "Harbor",
    "Heritage",
    "Keystone",
    "Liberty",
    "Meridian",
    "Oakstone",
    "Pioneer",
    "Summit",
]
COMPANY_SERVICES = ["Title", "Closing", "Escrow", "Realty", "Legal", "Settlement"]
FIRST_NAMES = [
    "Alex",
    "Avery",
    "Cameron",
    "Casey",
    "Dana",
    "Elliot",
    "Jordan",
    "Morgan",
    "Parker",
    "Quinn",
    "Riley",
    "Taylor",
]
LAST_NAMES = [
    "Bennett",
    "Campbell",
    "Diaz",
    "Foster",
    "Garcia",
    "Hughes",
    "Kim",
    "Morgan",
    "Patel",
    "Reed",
    "Sullivan",
    "Walker",
]
CITIES = [
    ("Tampa", "FL", "33602"),
    ("Orlando", "FL", "32801"),
    ("Miami", "FL", "33130"),
    ("Jacksonville", "FL", "32202"),
    ("Fort Lauderdale", "FL", "33301"),
    ("Sarasota", "FL", "34236"),
    ("Atlanta", "GA", "30303"),
    ("Charlotte", "NC", "28202"),
]
PRODUCT_LINES = [
    "Municipal Lien Search",
    "Tax Search",
    "HOA Search",
    "Estoppel",
    "Title Search",
]
JOB_TITLES = ["Closer", "Processor", "Attorney", "Office Manager", "Sales Manager"]


@dataclass(frozen=True)
class GenerationConfig:
    output_dir: Path
    seed: int = 2026
    company_count: int = 500
    contact_count: int = 1_200
    order_count: int = 10_000
    batch_count: int = 3
    overwrite: bool = False


def _iso_timestamp(day: date, hour: int = 12) -> str:
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC).isoformat()


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        raise ValueError(f"Cannot write an empty CSV file: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def _company_name_variant(name: str, index: int) -> str:
    variants = (
        name,
        f"{name}, LLC",
        name.replace(" and ", " & "),
        name.upper(),
        f"{name} Inc",
    )
    return variants[index % len(variants)]


def _prepare_output(output_dir: Path, overwrite: bool) -> None:
    existing = list(output_dir.glob("batch_*")) if output_dir.exists() else []
    summary = output_dir / "generation_summary.json"
    if (existing or summary.exists()) and not overwrite:
        raise FileExistsError(
            f"Generated data already exists in {output_dir}. Use --overwrite to replace it."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for path in existing:
            if path.is_dir():
                shutil.rmtree(path)
        summary.unlink(missing_ok=True)


def generate_synthetic_data(config: GenerationConfig) -> dict[str, Any]:
    """Generate deterministic CRM and ERP source batches with realistic data issues."""

    if config.batch_count < 2:
        raise ValueError("At least two batches are required to demonstrate incremental loading.")
    if min(config.company_count, config.contact_count, config.order_count) < 1:
        raise ValueError("Company, contact, and order counts must all be positive.")

    _prepare_output(config.output_dir, config.overwrite)
    rng = random.Random(config.seed)
    base_day = date(2026, 1, 5)

    companies: list[dict[str, Any]] = []
    erp_customers: list[dict[str, Any]] = []
    for index in range(1, config.company_count + 1):
        city, state, postal_code = CITIES[(index - 1) % len(CITIES)]
        canonical_name = (
            f"{COMPANY_PREFIXES[(index - 1) % len(COMPANY_PREFIXES)]} "
            f"{COMPANY_SERVICES[((index - 1) // len(COMPANY_PREFIXES)) % len(COMPANY_SERVICES)]} "
            f"{city} {index:04d}"
        )
        domain_stem = normalize_company_name(canonical_name).replace(" ", "")
        domain = f"{domain_stem}.com"
        erp_customer_id = f"ERP{index:06d}"
        crm_company_id = f"CRM{index:06d}"
        address = f"{100 + index} Market Street"
        source_updated_at = _iso_timestamp(base_day)
        companies.append(
            {
                "company_id": crm_company_id,
                "company_name": _company_name_variant(canonical_name, index),
                "domain": "" if index % 17 == 0 else domain,
                "phone": f"+1-813-555-{index % 10_000:04d}",
                "address": address,
                "city": city,
                "state": state,
                "postal_code": postal_code,
                "owner_id": f"OWN{((index - 1) % 8) + 1:03d}",
                "erp_customer_id": erp_customer_id if index % 5 != 0 else "",
                "source_updated_at": source_updated_at,
            }
        )
        erp_customers.append(
            {
                "customer_id": erp_customer_id,
                "company_name": canonical_name,
                "email_domain": domain,
                "address": address,
                "city": city,
                "state": state,
                "postal_code": postal_code,
                "is_active": "true" if index % 23 else "false",
                "source_updated_at": source_updated_at,
            }
        )

    contacts: list[dict[str, Any]] = []
    for index in range(1, config.contact_count + 1):
        company = companies[(index - 1) % len(companies)]
        first_name = FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]
        last_name = LAST_NAMES[((index - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]
        domain = company["domain"] or f"unknown-company-{index}.example"
        email = f"{first_name}.{last_name}{index}@{domain}".lower()
        if index % 53 == 0:
            email = email.replace("@", ".invalid-")
        contacts.append(
            {
                "contact_id": f"CON{index:07d}",
                "company_id": company["company_id"],
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": f"+1-941-555-{index % 10_000:04d}",
                "job_title": JOB_TITLES[(index - 1) % len(JOB_TITLES)],
                "source_updated_at": _iso_timestamp(base_day),
            }
        )

    orders: list[dict[str, Any]] = []
    for index in range(1, config.order_count + 1):
        customer = erp_customers[rng.randrange(len(erp_customers))]
        order_day = base_day - timedelta(days=rng.randrange(0, 180))
        amount = round(rng.uniform(85, 725), 2)
        status_roll = rng.random()
        status = (
            "Completed" if status_roll < 0.90 else "Cancelled" if status_roll < 0.96 else "Open"
        )
        orders.append(
            {
                "order_id": f"ORD{index:08d}",
                "customer_id": customer["customer_id"],
                "order_date": order_day.isoformat(),
                "product_line": PRODUCT_LINES[(index - 1) % len(PRODUCT_LINES)],
                "order_status": status,
                "order_amount": f"{amount:.2f}",
                "source_updated_at": _iso_timestamp(base_day + timedelta(days=index % 3)),
            }
        )

    company_slices: list[list[dict[str, Any]]] = [[] for _ in range(config.batch_count)]
    customer_slices: list[list[dict[str, Any]]] = [[] for _ in range(config.batch_count)]
    contact_slices: list[list[dict[str, Any]]] = [[] for _ in range(config.batch_count)]
    order_slices: list[list[dict[str, Any]]] = [[] for _ in range(config.batch_count)]

    for index, row in enumerate(companies):
        batch_index = min(index * config.batch_count // len(companies), config.batch_count - 1)
        company_slices[batch_index].append(row)
        customer_slices[batch_index].append(erp_customers[index])
    for index, row in enumerate(contacts):
        batch_index = min(index * config.batch_count // len(contacts), config.batch_count - 1)
        contact_slices[batch_index].append(row)
    rng.shuffle(orders)
    for index, row in enumerate(orders):
        batch_index = min(index * config.batch_count // len(orders), config.batch_count - 1)
        order_slices[batch_index].append(row)

    # Add changing CRM records to later batches so the latest-record logic can be demonstrated.
    for batch_index in range(1, config.batch_count):
        update_count = max(1, config.company_count // 20)
        for offset in range(update_count):
            source = companies[(batch_index * update_count + offset) % len(companies)].copy()
            source["owner_id"] = f"OWN{((batch_index + offset) % 8) + 1:03d}"
            source["source_updated_at"] = _iso_timestamp(base_day + timedelta(days=batch_index))
            company_slices[batch_index].append(source)

        # Exact duplicates test idempotency and source duplicate handling.
        duplicate_count = min(10, len(order_slices[batch_index - 1]))
        order_slices[batch_index].extend(order_slices[batch_index - 1][:duplicate_count])

    # Invalid records are intentionally generated so quarantine behavior is visible.
    contact_slices[-1].append(
        {
            "contact_id": "CON_INVALID_EMAIL",
            "company_id": companies[0]["company_id"],
            "first_name": "Invalid",
            "last_name": "Email",
            "email": "not-an-email",
            "phone": "+1-000-000-0000",
            "job_title": "Test Record",
            "source_updated_at": _iso_timestamp(base_day + timedelta(days=config.batch_count)),
        }
    )
    order_slices[-1].append(
        {
            "order_id": "ORD_INVALID_AMOUNT",
            "customer_id": erp_customers[0]["customer_id"],
            "order_date": base_day.isoformat(),
            "product_line": PRODUCT_LINES[0],
            "order_status": "Completed",
            "order_amount": "-100.00",
            "source_updated_at": _iso_timestamp(base_day + timedelta(days=config.batch_count)),
        }
    )

    batch_summaries: list[dict[str, Any]] = []
    for batch_index in range(config.batch_count):
        batch_number = batch_index + 1
        batch_id = f"batch_{batch_number:02d}"
        batch_dir = config.output_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        _write_jsonl(batch_dir / "crm_companies.jsonl", company_slices[batch_index])
        _write_jsonl(batch_dir / "crm_contacts.jsonl", contact_slices[batch_index])
        _write_csv(batch_dir / "erp_customers.csv", customer_slices[batch_index])
        _write_csv(batch_dir / "erp_orders.csv", order_slices[batch_index])
        manifest = {
            "batch_id": batch_id,
            "generated_at": _iso_timestamp(base_day + timedelta(days=batch_index)),
            "scenario": (
                "initial load"
                if batch_index == 0
                else "incremental records, source updates, and duplicate delivery"
            ),
            "files": {
                "crm_companies.jsonl": len(company_slices[batch_index]),
                "crm_contacts.jsonl": len(contact_slices[batch_index]),
                "erp_customers.csv": len(customer_slices[batch_index]),
                "erp_orders.csv": len(order_slices[batch_index]),
            },
        }
        (batch_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        batch_summaries.append(manifest)

    summary = {
        "seed": config.seed,
        "requested_counts": {
            "companies": config.company_count,
            "contacts": config.contact_count,
            "orders": config.order_count,
            "batches": config.batch_count,
        },
        "generated_batches": batch_summaries,
        "documented_scenarios": [
            "CRM and ERP identifiers",
            "company-name variations",
            "missing CRM-to-ERP identifiers",
            "incremental updates",
            "duplicate source delivery",
            "late-arriving orders",
            "invalid records for quarantine",
        ],
    }
    (config.output_dir / "generation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
