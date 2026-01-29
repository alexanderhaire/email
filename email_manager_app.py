import pyodbc
from datetime import datetime
from invoice_emailer import get_connection_string
from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)
CUSTOMER_FILE = "customer_emails.json"
VENDOR_FILE = "vendor_emails.json"
GLOBAL_CONFIG_FILE = "global_config.json"

def get_db_connection():
    return pyodbc.connect(get_connection_string())

def get_entities_with_emails(table_name, id_col, name_col, address_col, master_type):
    """Fetch entities (Customers/Vendors) with their GP-stored email addresses"""
    items = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"""
        SELECT 
            m.{id_col}, 
            m.{name_col}, 
            COALESCE(inet.EmailToAddress, inet.INET1, '') as Email
        FROM {table_name} m
        LEFT JOIN SY01200 inet ON inet.Master_Type = ? 
            AND inet.Master_ID = m.{id_col} 
            AND inet.ADRSCODE = m.{address_col}
        ORDER BY m.{id_col}
        """
        cursor.execute(query, (master_type,))
        for row in cursor.fetchall():
            items.append({
                "id": str(row[0]).strip(),
                "name": str(row[1]).strip(),
                "gp_email": str(row[2]).strip() if row[2] else ""
            })
        conn.close()
    except Exception as e:
        print(f"Error fetching from {table_name}: {e}")
    
    print(f"Loaded {len(items)} items from {table_name} ({master_type})")
    return items

def load_json(filename):
    if not os.path.exists(filename):
        # Create default if global config missing
        if filename == GLOBAL_CONFIG_FILE:
            return {"invoice_cc": "", "po_cc": ""}
        return {}
    
    with open(filename, 'r') as f:
        try:
            data = json.load(f)
            # Migration/Normalization: Convert string values to objects on load
            # (Skip for global config which is flat)
            if filename != GLOBAL_CONFIG_FILE:
                normalized = {}
                for k, v in data.items():
                    if isinstance(v, str):
                        normalized[k] = {"to": v, "cc": ""}
                    else:
                        normalized[k] = v
                return normalized
            return data
        except:
            if filename == GLOBAL_CONFIG_FILE:
                return {"invoice_cc": "", "po_cc": ""}
            return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def root():
    return redirect(url_for('invoices'))

@app.route('/invoices')
def invoices():
    mappings = load_json(CUSTOMER_FILE)
    global_config = load_json(GLOBAL_CONFIG_FILE)
    sorted_mappings = dict(sorted(mappings.items()))
    # Optimization: Don't load all 5000+ customers on load
    return render_template('index.html', 
                         mode="invoices",
                         title="Invoice Email Manager", 
                         entity_name="Customer",
                         mappings=sorted_mappings, 
                         entities=[], # Load via API
                         global_cc=global_config.get("invoice_cc", ""))

@app.route('/purchasing')
def purchasing():
    mappings = load_json(VENDOR_FILE)
    global_config = load_json(GLOBAL_CONFIG_FILE)
    sorted_mappings = dict(sorted(mappings.items()))
    # Optimization: Don't load all vendors on load
    return render_template('index.html', 
                         mode="purchasing",
                         title="Purchasing Email Manager", 
                         entity_name="Vendor",
                         mappings=sorted_mappings, 
                         entities=[], # Load via API
                         global_cc=global_config.get("po_cc", ""))

def search_entities_db(table_name, id_col, name_col, address_col, master_type, search_term):
    """Search for entities matching term"""
    items = []
    with open("debug_search.log", "a") as logf:
        logf.write(f"\n--- Search Search: {datetime.now()} ---\n")
        logf.write(f"Table: {table_name}, MasterType: {master_type}, Term: {search_term}\n")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Safe search with parameterized query
        search_pattern = f"%{search_term}%"
        
        query = f"""
        SELECT TOP 50
            m.{id_col}, 
            m.{name_col}, 
            COALESCE(inet.EmailToAddress, inet.INET1, '') as Email
        FROM {table_name} m
        LEFT JOIN SY01200 inet ON inet.Master_Type = ? 
            AND inet.Master_ID = m.{id_col} 
            AND inet.ADRSCODE = m.{address_col}
        WHERE m.{id_col} LIKE ? OR m.{name_col} LIKE ?
        ORDER BY m.{id_col}
        """
        print(f"DEBUG: Executing search for '{search_term}' in {table_name}")
        cursor.execute(query, (master_type, search_pattern, search_pattern))
        for row in cursor.fetchall():
            items.append({
                "id": str(row[0]).strip(),
                "name": str(row[1]).strip(),
                "gp_email": str(row[2]).strip() if row[2] else ""
            })
        
        with open("debug_search.log", "a") as logf:
            logf.write(f"SQL: {query.replace('?', '{}').format(master_type, search_pattern, search_pattern)}\n")
            logf.write(f"Results Found: {len(items)}\n")

        print(f"DEBUG: Found {len(items)} results")
        conn.close()
    except Exception as e:
        with open("debug_search.log", "a") as logf:
            logf.write(f"ERROR: {e}\n")
        print(f"Error searching {table_name}: {e}")
        import traceback
        traceback.print_exc()
        
    return items

@app.route('/api/search')
def search_api():
    mode = request.args.get('mode', 'invoices')
    query = request.args.get('q', '').strip()
    
    if not query:
        return json.dumps([])
        
    if mode == 'invoices':
        results = search_entities_db("RM00101", "CUSTNMBR", "CUSTNAME", "ADRSCODE", "CUS", query)
    else:
        results = search_entities_db("PM00200", "VENDORID", "VENDNAME", "VADDCDPR", "VEN", query)
        
    return json.dumps(results)

@app.route('/save', methods=['POST'])
def save():
    mode = request.form.get('mode')
    entity_id = request.form.get('entity_id').strip().upper()
    
    # Get inputs
    new_to = request.form.get('email_to', '').strip()
    new_cc = request.form.get('email_cc', '').strip()
    
    filename = CUSTOMER_FILE if mode == 'invoices' else VENDOR_FILE
    
    if entity_id and new_to:
        data = load_json(filename)
        
        # Merge if exists
        if entity_id in data:
            current_data = data[entity_id]
            # Helper to merge comma-separated strings
            def merge_lists(old_str, new_str):
                old_list = [x.strip() for x in old_str.replace(';', ',').split(',') if x.strip()]
                new_list = [x.strip() for x in new_str.replace(';', ',').split(',') if x.strip()]
                combined = []
                seen = set()
                for email in old_list + new_list:
                    if email.lower() not in seen:
                        combined.append(email)
                        seen.add(email.lower())
                return ", ".join(combined)

            final_to = merge_lists(current_data.get("to", ""), new_to)
            final_cc = merge_lists(current_data.get("cc", ""), new_cc)
            
            data[entity_id] = {
                "to": final_to,
                "cc": final_cc
            }
        else:
            # New entry
            data[entity_id] = {
                "to": new_to,
                "cc": new_cc
            }
            
        save_json(filename, data)
        
    return redirect(url_for(mode))

@app.route('/save_global', methods=['POST'])
def save_global():
    mode = request.form.get('mode')
    global_cc = request.form.get('global_cc', '').strip()
    
    data = load_json(GLOBAL_CONFIG_FILE)
    
    if mode == 'invoices':
        data['invoice_cc'] = global_cc
    else:
        data['po_cc'] = global_cc
        
    save_json(GLOBAL_CONFIG_FILE, data)
    return redirect(url_for(mode))

@app.route('/delete', methods=['POST'])
def delete():
    mode = request.form.get('mode')
    entity_id = request.form.get('entity_id')
    
    filename = CUSTOMER_FILE if mode == 'invoices' else VENDOR_FILE
    
    data = load_json(filename)
    if entity_id in data:
        del data[entity_id]
        save_json(filename, data)
        
    return redirect(url_for(mode))

if __name__ == '__main__':
    import socket
    
    # Find local IP
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "Unknown"

    print("="*40)
    print(f"  Local:   http://localhost:5000")
    print(f"  Network: http://{local_ip}:5000")
    print("="*40)

    from waitress import serve
    # Use waitress for a robust production server on Windows
    try:
        import waitress
        serve(app, host='0.0.0.0', port=5000)
    except ImportError:
        app.run(host='0.0.0.0', port=5000, debug=True)
