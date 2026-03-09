import datetime
from generate_daily_production_report import generate_report, generate_ai_summary

result = generate_report("2026-02-19")
if result:
    _, prod_data, orders_data, target_date = result
    subject, body = generate_ai_summary(prod_data, orders_data, target_date)
    print("SUBJECT:")
    print(subject)
    print("\nBODY HTML:")
    print(body)
