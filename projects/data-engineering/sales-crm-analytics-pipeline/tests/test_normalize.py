from sales_crm_pipeline.normalize import (
    is_valid_email,
    normalize_company_name,
    normalize_domain,
    record_hash,
)


def test_company_name_normalization_removes_legal_suffixes_and_punctuation() -> None:
    assert normalize_company_name("Atlantic Title & Escrow, LLC") == "atlantic title and escrow"


def test_domain_normalization_removes_protocol_and_www() -> None:
    assert normalize_domain("https://www.Example.com/path") == "example.com"


def test_email_validation() -> None:
    assert is_valid_email("analyst@example.com")
    assert not is_valid_email("not-an-email")


def test_record_hash_does_not_depend_on_key_order() -> None:
    assert record_hash({"a": 1, "b": 2}) == record_hash({"b": 2, "a": 1})
