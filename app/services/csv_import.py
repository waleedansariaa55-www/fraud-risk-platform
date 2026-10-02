import csv
import io
from datetime import datetime

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.core.config import MAX_CSV_ROWS_PER_IMPORT
from app.models.transaction import Transaction, TransactionSource, PaymentMethod
from app.schemas.transaction_schemas import CSVImportResult

REQUIRED_COLUMNS = {"external_transaction_id", "customer_id", "amount", "transaction_datetime"}

OPTIONAL_COLUMNS = {
    "currency", "payment_method", "ip_address", "location", "device_info",
    "customer_account_age_days", "previous_transaction_count", "notes",
}


def _parse_payment_method(value: str) -> PaymentMethod:
    if not value:
        return PaymentMethod.OTHER
    value_norm = value.strip().lower().replace(" ", "_")
    try:
        return PaymentMethod(value_norm)
    except ValueError:
        return PaymentMethod.OTHER


def import_transactions_from_csv(
    file_bytes: bytes,
    business_id: int,
    created_by_user_id: int,
    db: Session,
) -> CSVImportResult:
    """
    Parses a CSV of transactions and bulk-inserts valid rows.
    Required columns: external_transaction_id, customer_id, amount, transaction_datetime
    Optional columns: currency, payment_method, ip_address, location, device_info,
                       customer_account_age_days, previous_transaction_count, notes
    Invalid rows are skipped and reported in `errors`, without aborting the whole import.
    """
    try:
        decoded = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = file_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))

    if reader.fieldnames is None:
        return CSVImportResult(total_rows=0, imported=0, failed=0, errors=["CSV file is empty."])

    header_set = {h.strip() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - header_set
    if missing:
        return CSVImportResult(
            total_rows=0, imported=0, failed=0,
            errors=[f"Missing required column(s): {', '.join(sorted(missing))}"],
        )

    rows = list(reader)
    total_rows = len(rows)
    if total_rows > MAX_CSV_ROWS_PER_IMPORT:
        return CSVImportResult(
            total_rows=total_rows, imported=0, failed=total_rows,
            errors=[f"CSV exceeds max allowed rows ({MAX_CSV_ROWS_PER_IMPORT})."],
        )

    imported = 0
    errors: list[str] = []
    to_insert = []

    for idx, row in enumerate(rows, start=2):  # start=2: header is row 1
        try:
            ext_id = (row.get("external_transaction_id") or "").strip()
            customer_id = (row.get("customer_id") or "").strip()
            amount_raw = (row.get("amount") or "").strip()
            dt_raw = (row.get("transaction_datetime") or "").strip()

            if not ext_id or not customer_id or not amount_raw or not dt_raw:
                raise ValueError("missing required field(s)")

            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError("amount must be positive")

            txn_dt = date_parser.parse(dt_raw)

            age_raw = (row.get("customer_account_age_days") or "").strip()
            prev_raw = (row.get("previous_transaction_count") or "").strip()

            txn = Transaction(
                external_transaction_id=ext_id,
                business_id=business_id,
                customer_id=customer_id,
                amount=amount,
                currency=(row.get("currency") or "USD").strip() or "USD",
                transaction_datetime=txn_dt,
                payment_method=_parse_payment_method(row.get("payment_method", "")),
                ip_address=(row.get("ip_address") or "").strip() or None,
                location=(row.get("location") or "").strip() or None,
                device_info=(row.get("device_info") or "").strip() or None,
                customer_account_age_days=int(age_raw) if age_raw else None,
                previous_transaction_count=int(prev_raw) if prev_raw else None,
                source=TransactionSource.CSV_IMPORT,
                created_by_user_id=created_by_user_id,
                notes=(row.get("notes") or "").strip() or None,
            )
            to_insert.append(txn)
            imported += 1
        except Exception as e:
            errors.append(f"Row {idx}: {e}")

    if to_insert:
        db.bulk_save_objects(to_insert)
        db.commit()

    return CSVImportResult(
        total_rows=total_rows,
        imported=imported,
        failed=total_rows - imported,
        errors=errors[:50],  # cap error list so response doesn't balloon
    )
