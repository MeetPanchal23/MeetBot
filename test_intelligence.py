import sys
import ipo_intelligence

sys.stdout.reconfigure(encoding='utf-8')

test_queries = [
    "money view Ltd ipo name",
    "Tata Capital",
    "Nova Consumer"
]

for q in test_queries:
    print(f"\n==========================================")
    print(f"TESTING QUERY: '{q}'")
    print(f"==========================================")
    report_data = ipo_intelligence.analyze_ipo_comprehensive(q)
    formatted_msg = ipo_intelligence.format_ipo_analysis_report(report_data)
    print(formatted_msg)
