from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from sales_crm_pipeline.config import PROJECT_ROOT, Settings
from sales_crm_pipeline.normalize import is_valid_email, record_hash

SOURCE_CONFIG = {
    "crm_companies": {
        "filename": "crm_companies.jsonl",
        "record_id": "company_id",
        "insert_sql": """
            insert into raw.crm_companies (
                company_id, company_name, domain, phone, address, city, state,
                postal_code, owner_id, erp_customer_id, source_updated_at,
                batch_id, source_file, record_hash
            ) values (
                %(company_id)s, %(company_name)s, %(domain)s, %(phone)s,
                %(address)s, %(city)s, %(state)s, %(postal_code)s,
                %(owner_id)s, %(erp_customer_id)s, %(source_updated_at)s,
                %(batch_id)s, %(source_file)s, %(record_hash)s
            ) on conflict (company_id, record_hash) do nothing
        """,
    },
    "crm_contacts": {
        "filename": "crm_contacts.jsonl",
        "record_id": "contact_id",
        "insert_sql": """
            insert into raw.crm_contacts (
                contact_id, company_id, first_name, last_name, email, phone,
                job_title, source_updated_at, batch_id, source_file, record_hash
            ) values (
                %(contact_id)s, %(company_id)s, %(first_name)s, %(last_name)s,
                %(email)s, %(phone)s, %(job_title)s, %(source_updated_at)s,
                %(batch_id)s, %(source_file)s, %(record_hash)s
            ) on conflict (contact_id, record_hash) do nothing
        """,
    },
    "erp_customers": {
        "filename": "erp_customers.csv",
        "record_id": "customer_id",
        "insert_sql": """
            insert into raw.erp_customers (
                customer_id, company_name, email_domain, address, city, state,
                postal_code, is_active, source_updated_at, batch_id,
                source_file, record_hash
            ) values (
                %(customer_id)s, %(company_name)s, %(email_domain)s,
                %(address)s, %(city)s, %(state)s, %(postal_code)s,
                %(is_active)s, %(source_updated_at)s, %(batch_id)s,
                %(source_file)s, %(record_hash)s
            ) on conflict (customer_id, record_hash) do nothing
        """,
    },
    "erp_orders": {
        "filename": "erp_orders.csv",
        "record_id": "order_id",
        "insert_sql": """
            insert into raw.erp_orders (
                order_id, customer_id, order_date, product_line, order_status,
                order_amount, source_updated_at, batch_id, source_file, record_hash
            ) values (
                %(order_id)s, %(customer_id)s, %(order_date)s, %(product_line)s,
                %(order_status)s, %(order_amount)s, %(source_updated_at)s,
                %(batch_id)s, %(source_file)s, %(record_hash)s
            ) on conflict (order_id, record_hash) do nothing
        """,
    },
}


def _none_if_blank(value: Any) -> Any:
    return None if value is None or str(value).strip() == "" else value


def _require(row: dict[str, Any], field: str) -> str:
    value = _none_if_blank(row.get(field))
    if value is None:
        raise ValueError(f"{field} is required")
    return str(value).strip()


def _timestamp(value: Any) -> datetime:
    raw = _require({"value": value}, "value")
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _state(value: Any) -> str:
    state = _require({"state": value}, "state").upper()
    if len(state) != 2 or not state.isalpha():
        raise ValueError("state must be a two-letter abbreviation")
    return state


def _validated_record(source_name: str, row: dict[str, Any]) -> dict[str, Any]:
    cleaned = {key: _none_if_blank(value) for key, value in row.items()}

    if source_name == "crm_companies":
        cleaned["company_id"] = _require(cleaned, "company_id")
        cleaned["company_name"] = _require(cleaned, "company_name")
        cleaned["state"] = _state(cleaned.get("state"))
        cleaned["source_updated_at"] = _timestamp(cleaned.get("source_updated_at"))
    elif source_name == "crm_contacts":
        cleaned["contact_id"] = _require(cleaned, "contact_id")
        email = _require(cleaned, "email").lower()
        if not is_valid_email(email):
            raise ValueError("email is not valid")
        cleaned["email"] = email
        cleaned["source_updated_at"] = _timestamp(cleaned.get("source_updated_at"))
    elif source_name == "erp_customers":
        cleaned["customer_id"] = _require(cleaned, "customer_id")
        cleaned["company_name"] = _require(cleaned, "company_name")
        cleaned["state"] = _state(cleaned.get("state"))
        active = _require(cleaned, "is_active").lower()
        if active not in {"true", "false"}:
            raise ValueError("is_active must be true or false")
        cleaned["is_active"] = active == "true"
        cleaned["source_updated_at"] = _timestamp(cleaned.get("source_updated_at"))
    elif source_name == "erp_orders":
        cleaned["order_id"] = _require(cleaned, "order_id")
        cleaned["customer_id"] = _require(cleaned, "customer_id")
        cleaned["product_line"] = _require(cleaned, "product_line")
        cleaned["order_status"] = _require(cleaned, "order_status")
        cleaned["order_date"] = date.fromisoformat(_require(cleaned, "order_date"))
        try:
            amount = Decimal(_require(cleaned, "order_amount"))
        except InvalidOperation as exc:
            raise ValueError("order_amount is not numeric") from exc
        if amount <= 0:
            raise ValueError("order_amount must be greater than zero")
        cleaned["order_amount"] = amount
        cleaned["source_updated_at"] = _timestamp(cleaned.get("source_updated_at"))
    else:
        raise ValueError(f"Unsupported source: {source_name}")
    return cleaned


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _read_csv(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def _read_source(path: Path) -> Iterable[dict[str, Any]]:
    return _read_jsonl(path) if path.suffix == ".jsonl" else _read_csv(path)


def initialize_database(
    connection: psycopg.Connection[Any], schema_path: Path | None = None
) -> None:
    ddl_path = schema_path or PROJECT_ROOT / "sql" / "001_raw_schema.sql"
    connection.execute(ddl_path.read_text(encoding="utf-8"))


def load_generated_data(
    settings: Settings,
    input_dir: Path,
    schema_path: Path | None = None,
) -> dict[str, int | str]:
    """Load all generated batches and quarantine records that fail validation."""

    batch_dirs = sorted(path for path in input_dir.glob("batch_*") if path.is_dir())
    if not batch_dirs:
        raise FileNotFoundError(f"No generated batches were found in {input_dir}")

    run_id = uuid4()
    totals = {
        "batches_processed": 0,
        "loaded_records": 0,
        "duplicate_records": 0,
        "rejected_records": 0,
    }

    with psycopg.connect(settings.database_url) as connection:
        initialize_database(connection, schema_path)
        connection.execute(
            """
            insert into audit.pipeline_runs (run_id, status, input_path)
            values (%s, 'running', %s)
            """,
            (run_id, str(input_dir.resolve())),
        )
        connection.commit()

        try:
            for batch_dir in batch_dirs:
                batch_id = batch_dir.name
                for source_name, source_config in SOURCE_CONFIG.items():
                    source_path = batch_dir / str(source_config["filename"])
                    if not source_path.exists():
                        raise FileNotFoundError(f"Expected source file is missing: {source_path}")

                    valid_records: list[dict[str, Any]] = []
                    rejected_records: list[dict[str, Any]] = []
                    for raw_row in _read_source(source_path):
                        try:
                            record = _validated_record(source_name, raw_row)
                            record.update(
                                {
                                    "batch_id": batch_id,
                                    "source_file": source_path.name,
                                    "record_hash": record_hash(raw_row),
                                }
                            )
                            valid_records.append(record)
                        except (TypeError, ValueError) as exc:
                            record_id_field = str(source_config["record_id"])
                            rejected_records.append(
                                {
                                    "run_id": run_id,
                                    "batch_id": batch_id,
                                    "source_name": source_name,
                                    "source_file": source_path.name,
                                    "source_record_id": raw_row.get(record_id_field),
                                    "rejection_reason": str(exc),
                                    "raw_payload": Jsonb(raw_row),
                                }
                            )

                    if valid_records:
                        cursor = connection.cursor()
                        cursor.executemany(str(source_config["insert_sql"]), valid_records)
                        loaded_count = max(cursor.rowcount, 0)
                        totals["loaded_records"] += loaded_count
                        totals["duplicate_records"] += len(valid_records) - loaded_count
                    if rejected_records:
                        connection.cursor().executemany(
                            """
                            insert into audit.rejected_records (
                                run_id, batch_id, source_name, source_file,
                                source_record_id, rejection_reason, raw_payload
                            ) values (
                                %(run_id)s, %(batch_id)s, %(source_name)s,
                                %(source_file)s, %(source_record_id)s,
                                %(rejection_reason)s, %(raw_payload)s
                            )
                            """,
                            rejected_records,
                        )
                        totals["rejected_records"] += len(rejected_records)
                totals["batches_processed"] += 1
                connection.commit()

            connection.execute(
                """
                update audit.pipeline_runs
                set completed_at = current_timestamp,
                    status = 'succeeded',
                    batches_processed = %s,
                    loaded_records = %s,
                    duplicate_records = %s,
                    rejected_records = %s
                where run_id = %s
                """,
                (
                    totals["batches_processed"],
                    totals["loaded_records"],
                    totals["duplicate_records"],
                    totals["rejected_records"],
                    run_id,
                ),
            )
            connection.commit()
        except Exception as exc:
            connection.rollback()
            connection.execute(
                """
                update audit.pipeline_runs
                set completed_at = current_timestamp,
                    status = 'failed',
                    error_message = %s
                where run_id = %s
                """,
                (str(exc), run_id),
            )
            connection.commit()
            raise

    return {"run_id": str(run_id), **totals}
