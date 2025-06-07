from supabase import create_client, Client
import os
import math
from flask import request
from datetime import datetime, date
import uuid # Import uuid for ID generation

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

        # Add ordering by input_timestamp descending
        query = query.order('input_timestamp', desc=True)

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

def add_cutting_record(record_data: dict) -> dict:
    """
    Adds a new cutting record to Supabase.
    Args:
        record_data: Dictionary containing the record data.
    Returns:
        The inserted record data if successful, otherwise raises an exception.
    """
    try:
        # Ensure ID is generated if not provided
        if 'id' not in record_data or not record_data['id']:
            record_data['id'] = str(uuid.uuid4())
        
        # Ensure input_timestamp is set
        if 'input_timestamp' not in record_data or not record_data['input_timestamp']:
            record_data['input_timestamp'] = datetime.now().isoformat()

        # Handle date conversion if needed (Supabase expects ISO format)
        if 'date' in record_data and isinstance(record_data['date'], date):
            record_data['date'] = record_data['date'].isoformat()

        response = supabase.table('tab_cutting').insert(record_data).execute()
        if response.data:
            return response.data[0]
        else:
            raise Exception(f"Supabase insert failed: {response.status_code} - {response.count}")
    except Exception as e:
        print(f"Error adding cutting record to Supabase: {e}")
        raise

def update_cutting_record(record_id: str, record_data: dict) -> dict:
    """
    Updates an existing cutting record in Supabase.
    Args:
        record_id: The ID of the record to update.
        record_data: Dictionary containing the updated data.
    Returns:
        The updated record data if successful, otherwise raises an exception.
    """
    try:
        # Remove ID from data to be updated, as it's used in the query filter
        data_to_update = record_data.copy()
        data_to_update.pop('id', None)

        # Ensure input_timestamp is updated
        data_to_update['input_timestamp'] = datetime.now().isoformat()

        # Handle date conversion if needed
        if 'date' in data_to_update and isinstance(data_to_update['date'], date):
            data_to_update['date'] = data_to_update['date'].isoformat()

        response = supabase.table('tab_cutting').update(data_to_update).eq('id', record_id).execute()
        if response.data:
            return response.data[0]
        else:
            raise Exception(f"Supabase update failed: {response.status_code} - {response.count}")
    except Exception as e:
        print(f"Error updating cutting record in Supabase: {e}")
        raise

def delete_cutting_records(record_ids: list[str]) -> int:
    """
    Deletes multiple cutting records from Supabase.
    Args:
        record_ids: List of IDs of records to delete.
    Returns:
        The number of records deleted if successful, otherwise raises an exception.
    """
    try:
        response = supabase.table('tab_cutting').delete().in_('id', record_ids).execute()
        # If we have data in the response, it means records were deleted
        if response.data is not None:
            return len(response.data)
        else:
            raise Exception("Failed to delete records: No response data from Supabase")
    except Exception as e:
        print(f"Error deleting cutting records from Supabase: {e}")
        raise 