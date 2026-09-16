import csv
import json
from pathlib import Path

from sales_crm_pipeline.generate import GenerationConfig, generate_synthetic_data


def test_generator_creates_incremental_batches_and_documented_bad_records(tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    summary = generate_synthetic_data(
        GenerationConfig(
            output_dir=output_dir,
            seed=2026,
            company_count=30,
            contact_count=75,
            order_count=240,
            batch_count=3,
        )
    )

    assert summary["requested_counts"]["batches"] == 3
    assert len(list(output_dir.glob("batch_*/manifest.json"))) == 3

    last_batch = output_dir / "batch_03"
    contact_text = (last_batch / "crm_contacts.jsonl").read_text(encoding="utf-8")
    assert "CON_INVALID_EMAIL" in contact_text

    with (last_batch / "erp_orders.csv").open(newline="", encoding="utf-8") as handle:
        orders = list(csv.DictReader(handle))
    assert any(row["order_id"] == "ORD_INVALID_AMOUNT" for row in orders)

    manifest = json.loads((last_batch / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["erp_orders.csv"] == len(orders)


def test_generator_is_deterministic_for_the_same_seed(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    config = {
        "seed": 42,
        "company_count": 12,
        "contact_count": 24,
        "order_count": 60,
        "batch_count": 3,
    }
    generate_synthetic_data(GenerationConfig(output_dir=first, **config))
    generate_synthetic_data(GenerationConfig(output_dir=second, **config))

    assert (first / "batch_01" / "erp_orders.csv").read_bytes() == (
        second / "batch_01" / "erp_orders.csv"
    ).read_bytes()
