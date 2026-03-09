import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(r"c:\Users\alexh\email")
sys.path.insert(0, str(project_root))

from scripts.raw_material_monitor import get_low_raw_materials

def check_count():
    try:
        print("Fetching low raw materials...")
        items = get_low_raw_materials()
        count = len(items)
        print(f"Total items matching criteria: {count}")
        
        print("\nItems:")
        for item in items:
            # Re-calculate available as per the monitor logic
            avail = item.qty_on_hand - item.qty_allocated
            print(f"- {item.item_number}: Available {avail:,.2f} < Order Point {item.gp_order_point:,.2f}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Print count at the end to ensure it's visible even if output is truncated
    print(f"\nFINAL COUNT: {count}")

if __name__ == "__main__":
    check_count()
