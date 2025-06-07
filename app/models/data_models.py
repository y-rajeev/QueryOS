from supabase import create_client, Client
import os
import math
from flask import request

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_paginated_data(table_name, search="", page=1, limit=10, columns: list[str] = None):
    """Helper function to get paginated data from Supabase"""
    try:
        offset = (page - 1) * limit
        
        # Dynamically select columns
        if columns:
            select_query_string = ",".join(columns)
            print(f"[DEBUG] Supabase select query string: {select_query_string}") # DEBUG
            query = supabase.table(table_name).select(select_query_string)
        else:
            print("[DEBUG] Supabase select query string: *") # DEBUG
            query = supabase.table(table_name).select("*")

        if search:
            search_conditions = []
            search_columns = ['unique_key', 'id', 'shipment_id', 'production', 'channel_abb']
            # Filter search_columns to only include those requested if columns is not None
            if columns:
                search_columns = [col for col in search_columns if col in columns]
            
            for column in search_columns:
                search_conditions.append(f"{column}.ilike.%{search}%")
            if search_conditions:
                query = query.or_(",".join(search_conditions))

        # Handle individual column filters
        for key, value in request.args.items():
            if key.startswith('filter_') and value.strip():
                column = key.replace('filter_', '')
                # Ensure the filtered column is part of the requested columns if columns are specified
                if columns and column not in columns:
                    continue # Skip filtering if column is not requested

                if column in ['po_qty', 'dispatched_qty', 'pending_qty']:
                    try:
                        num_value = float(value.strip())
                        query = query.eq(column, num_value)
                    except ValueError:
                        query = query.ilike(column, f"%{value.strip()}%")
                else:
                    query = query.ilike(column, f"%{value.strip()}%")

        data_response = query.execute()
        print(f"[DEBUG] Supabase raw data_response.data (before pagination): {data_response.data}") # DEBUG
        rows = data_response.data
        total_rows = len(rows)
        
        # Paginate after getting all data
        start_idx = offset
        end_idx = offset + limit
        rows = rows[start_idx:end_idx]
        print(f"[DEBUG] Rows after pagination: {rows}") # DEBUG
        
        # Headers should reflect the columns actually fetched/selected
        headers = columns if columns else (list(rows[0].keys()) if rows else [])
        print(f"[DEBUG] Final headers: {headers}") # DEBUG
        total_pages = math.ceil(total_rows / limit)

        return {
            "headers": headers,
            "rows": rows,
            "current_page": page,
            "total_pages": total_pages,
            "search": search
        }
    except Exception as e:
        print(f"Error in get_paginated_data: {e}") # Modified error message
        return {
            "headers": [],
            "rows": [],
            "current_page": 1,
            "total_pages": 1,
            "search": search,
            "error": "Failed to fetch data"
        } 