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

        # Define numeric fields for appropriate comparison types
        numeric_fields = ['pcs_pack', 'sets', 'produced_qty', 'rejection']

        # Handle filters (field, operator, value)
        filter_index = 0
        while True:
            field = request.args.get(f'filter_field_{filter_index}')
            operator = request.args.get(f'filter_operator_{filter_index}')
            value = request.args.get(f'filter_value_{filter_index}')

            if not field or not operator:
                break # No more filter conditions

            print(f"[DEBUG] Processing filter: field={field}, operator={operator}, value={value}")

            # Apply Supabase filter based on operator
            if operator == 'equal':
                if field in numeric_fields:
                    query = query.eq(field, float(value)) if value else query # Handle potential empty value for numeric fields
                else:
                    query = query.ilike(field, value) # Use ilike for case-insensitive string equality
            elif operator == 'not_equal':
                if field in numeric_fields:
                    query = query.neq(field, float(value)) if value else query
                else:
                    query = query.not_ilike(field, value)
            elif operator == 'like':
                query = query.ilike(field, f'%{value}%')
            elif operator == 'not_like':
                query = query.not_ilike(field, f'%{value}%')
            elif operator == 'is_set':
                query = query.not_eq(field, None)
            elif operator == 'not_set':
                query = query.eq(field, None)
            elif operator == 'gt':
                query = query.gt(field, float(value))
            elif operator == 'lt':
                query = query.lt(field, float(value))
            
            filter_index += 1

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

def get_monthly_production_data():
    """Fetches and aggregates monthly production data from Supabase."""
    try:
        # Query Supabase for production data, selecting date and produced_qty
        response = supabase.table('tab_production').select('date, produced_qty').execute()
        data = response.data

        # Initialize dictionary to store monthly production sums
        monthly_production = {}

        for record in data:
            record_date_str = record.get('date')
            produced_qty = record.get('produced_qty', 0)
            
            if record_date_str and isinstance(produced_qty, (int, float)):
                # Parse date string to get year and month
                try:
                    record_date = datetime.strptime(record_date_str, '%Y-%m-%d')
                    month_key = record_date.strftime('%Y-%m') # e.g., '2023-01'
                    
                    if month_key not in monthly_production:
                        monthly_production[month_key] = 0
                    monthly_production[month_key] += produced_qty
                except ValueError:
                    print(f"Skipping invalid date format: {record_date_str}")
                    continue

        # Sort the monthly data by month
        sorted_months = sorted(monthly_production.keys())
        months = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months] # e.g., 'Jan 2023'
        production_data = [monthly_production[m] for m in sorted_months]
        
        return months, production_data

    except Exception as e:
        print(f"Error in get_monthly_production_data: {e}")
        return [], [] 