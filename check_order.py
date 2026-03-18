"""Quick diagnostic: check why a specific order does/doesn't appear on the report."""
import sys
from db_pool import get_connection

def check_order(order_number: str):
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Check SOP10100 (Open Sales Order Header)
        print(f"\n=== Checking order '{order_number}' ===\n")

        cursor.execute("""
            SELECT SOPNUMBE, SOPTYPE, CUSTNAME, DOCID, REQSHIPDATE, VOIDSTTS
            FROM SOP10100
            WHERE SOPNUMBE LIKE ?
        """, f"%{order_number}%")
        headers = cursor.fetchall()

        if not headers:
            print("[SOP10100] NOT FOUND in open orders header.")
        else:
            for h in headers:
                print(f"[SOP10100] Found: SOPNUMBE={h.SOPNUMBE.strip()}, SOPTYPE={h.SOPTYPE}, "
                      f"CUSTNAME={h.CUSTNAME.strip()}, DOCID={h.DOCID.strip()}, "
                      f"REQSHIPDATE={h.REQSHIPDATE}, VOIDSTTS={h.VOIDSTTS}")
                soptype_labels = {1: "Quote", 2: "Order", 3: "Invoice", 4: "Return", 5: "Back Order", 6: "Fulfillment"}
                print(f"         -> SOPTYPE {h.SOPTYPE} = {soptype_labels.get(h.SOPTYPE, 'Unknown')}")
                if h.SOPTYPE != 2:
                    print("         -> ** NOT type 2 (Order) — this is why it's excluded from the report **")

        # 2. Check SOP10200 (Open Sales Order Lines)
        cursor.execute("""
            SELECT SOPNUMBE, SOPTYPE, ITEMNMBR, ITEMDESC, QUANTITY, QTYREMAI, UOFM
            FROM SOP10200
            WHERE SOPNUMBE LIKE ?
        """, f"%{order_number}%")
        lines = cursor.fetchall()

        if not lines:
            print("\n[SOP10200] NO LINE ITEMS found in open orders.")
        else:
            print(f"\n[SOP10200] {len(lines)} line(s) found:")
            for ln in lines:
                freight = ln.ITEMNMBR.strip().upper().startswith("FREIGHT")
                print(f"  - ITEM={ln.ITEMNMBR.strip()}, DESC={ln.ITEMDESC.strip()}, "
                      f"QTY={ln.QUANTITY}, QTYREMAI={ln.QTYREMAI}, UOFM={ln.UOFM.strip()}"
                      f"{' ** FREIGHT (excluded)' if freight else ''}"
                      f"{' ** QTYREMAI=0 (fully shipped)' if ln.QTYREMAI == 0 else ''}")

        # 3. Check SOP30200 (Sales Order History Header) — already invoiced/posted
        cursor.execute("""
            SELECT SOPNUMBE, SOPTYPE, CUSTNAME, DOCID, REQSHIPDATE
            FROM SOP30200
            WHERE SOPNUMBE LIKE ?
        """, f"%{order_number}%")
        history = cursor.fetchall()

        if history:
            print(f"\n[SOP30200] FOUND IN HISTORY (already posted/invoiced):")
            for h in history:
                print(f"  - SOPNUMBE={h.SOPNUMBE.strip()}, SOPTYPE={h.SOPTYPE}, "
                      f"CUSTNAME={h.CUSTNAME.strip()}, REQSHIPDATE={h.REQSHIPDATE}")
        else:
            print("\n[SOP30200] Not in history.")

        print("\n=== Done ===")

if __name__ == "__main__":
    order = sys.argv[1] if len(sys.argv) > 1 else "28384"
    check_order(order)
