import csv
import random
from datetime import datetime, timedelta

def generate_synthetic_dataset(output_dir="."):
    """
    Generates synthetic realistic statements for multi-provider reconciliation.
    Creates:
    - 1. Standard Bank Statement
    - 2. EcoCash Mobile Money Statement
    - 3. ERP General Ledger Extract
    """
    start_date = datetime(2026, 10, 1)
    
    bank_records = []
    erp_records = []
    ecocash_records = []

    # Generate 50 transactions
    for i in range(1, 51):
        txn_date = start_date + timedelta(days=i // 3, hours=random.randint(8, 17))
        amt = round(random.uniform(50.0, 2500.0), 2)
        ref = f"REF-2026-{1000 + i}"
        
        # 80% of transactions match perfectly
        if i <= 40:
            erp_records.append({
                "PostingDate": txn_date.strftime("%Y-%m-%d"),
                "ReferenceNo": ref,
                "Amount": f"{amt:.2f}",
                "EntryType": "CREDIT",
                "Description": f"Customer Order Payment {i}"
            })
            
            # Simulated settlement delay of 0 to 2 days in bank statement
            bank_date = txn_date + timedelta(days=random.choice([0, 1]))
            bank_records.append({
                "Date": bank_date.strftime("%Y-%m-%d"),
                "Reference": ref,
                "Narrative": f"SETTLEMENT ORDER {i}",
                "Debit": "",
                "Credit": f"{amt:.2f}",
                "Balance": "35000.00"
            })
        elif i <= 45:
            # Timing difference / Missing in bank statement (in-transit)
            erp_records.append({
                "PostingDate": txn_date.strftime("%Y-%m-%d"),
                "ReferenceNo": ref,
                "Amount": f"{amt:.2f}",
                "EntryType": "CREDIT",
                "Description": f"Customer Order In Transit {i}"
            })
        else:
            # Unidentified deposit in bank statement
            bank_records.append({
                "Date": txn_date.strftime("%Y-%m-%d"),
                "Reference": f"UNID-{i}",
                "Narrative": "DIRECT CASH DEPOSIT UNKNOWN SENDER",
                "Debit": "",
                "Credit": f"{amt:.2f}",
                "Balance": "38000.00"
            })

    print(f"Generated {len(bank_records)} bank records, {len(erp_records)} ERP ledger records.")

if __name__ == "__main__":
    generate_synthetic_dataset()
