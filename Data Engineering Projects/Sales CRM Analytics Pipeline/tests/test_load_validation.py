import pytest

from sales_crm_pipeline.load import _validated_record


def test_valid_order_is_converted_to_typed_values() -> None:
    record = _validated_record(
        "erp_orders",
        {
            "order_id": "ORD0001",
            "customer_id": "ERP0001",
            "order_date": "2026-01-01",
            "product_line": "Tax Search",
            "order_status": "Completed",
            "order_amount": "125.50",
            "source_updated_at": "2026-01-02T12:00:00+00:00",
        },
    )

    assert str(record["order_amount"]) == "125.50"
    assert record["order_date"].isoformat() == "2026-01-01"


def test_negative_order_amount_is_rejected() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        _validated_record(
            "erp_orders",
            {
                "order_id": "ORD0002",
                "customer_id": "ERP0001",
                "order_date": "2026-01-01",
                "product_line": "Tax Search",
                "order_status": "Completed",
                "order_amount": "-10.00",
                "source_updated_at": "2026-01-02T12:00:00+00:00",
            },
        )


def test_invalid_contact_email_is_rejected() -> None:
    with pytest.raises(ValueError, match="email is not valid"):
        _validated_record(
            "crm_contacts",
            {
                "contact_id": "CON0001",
                "company_id": "CRM0001",
                "first_name": "Test",
                "last_name": "Contact",
                "email": "not-an-email",
                "source_updated_at": "2026-01-02T12:00:00+00:00",
            },
        )
