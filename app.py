from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client, Client
import math
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# === Supabase Configuration ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLES = {
    "production": "tab_inprod",
    "cutting": "tab_cutting",
    "tab_production": "tab_production"
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_paginated_data(table_name, search="", page=1, limit=10):
    """Helper function to get paginated data from Supabase"""
    try:
        offset = (page - 1) * limit
        query = supabase.table(table_name).select("*")

        if search:
            search_conditions = []
            search_columns = ['unique_key', 'id', 'shipment_id', 'production', 'channel_abb']
            for column in search_columns:
                search_conditions.append(f"{column}.ilike.%{search}%")
            query = query.or_(",".join(search_conditions))

        # Handle individual column filters
        for key, value in request.args.items():
            if key.startswith('filter_') and value.strip():
                column = key.replace('filter_', '')
                if column in ['po_qty', 'dispatched_qty', 'pending_qty']:
                    try:
                        num_value = float(value.strip())
                        query = query.eq(column, num_value)
                    except ValueError:
                        query = query.ilike(column, f"%{value.strip()}%")
                else:
                    query = query.ilike(column, f"%{value.strip()}%")

        data_response = query.execute()
        rows = data_response.data
        total_rows = len(rows)
        
        # Paginate after getting all data
        start_idx = offset
        end_idx = offset + limit
        rows = rows[start_idx:end_idx]
        
        headers = list(rows[0].keys()) if rows else []
        total_pages = math.ceil(total_rows / limit)

        return {
            "headers": headers,
            "rows": rows,
            "current_page": page,
            "total_pages": total_pages,
            "search": search
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "headers": [],
            "rows": [],
            "current_page": 1,
            "total_pages": 1,
            "search": search,
            "error": "Failed to fetch data"
        }

@app.route("/")
def dashboard():
    # This will be your new dashboard/home page
    return render_template("dashboard.html")

@app.route("/production")
def production_data():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 10))
    
    data = get_paginated_data(TABLES["production"], search, page, limit)
    return render_template("production_data.html", **data)

@app.route("/cutting")
def cutting():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 10))
    
    data = get_paginated_data(TABLES["cutting"], search, page, limit)
    return render_template("cutting.html", **data)

@app.route("/tab-production")
def tab_production():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 10))
    
    data = get_paginated_data(TABLES["tab_production"], search, page, limit)
    return render_template("tab_production.html", **data)

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
