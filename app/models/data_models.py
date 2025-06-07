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

def get_article_summary_data(year_month=None):
    """Fetches and aggregates production data by product for a given month."""
    try:
        query = supabase.table('tab_production').select('date, product, produced_qty, rejection')
        
        if year_month:
            # Filter by the start and end of the specified month
            start_date = f'{year_month}-01'
            # Calculate end date for the month
            year, month = map(int, year_month.split('-'))
            if month == 12:
                end_date = f'{year + 1}-01-01'
            else:
                end_date = f'{year}-{month + 1:02d}-01'
            
            query = query.gte('date', start_date).lt('date', end_date)

        response = query.execute()
        data = response.data

        # Aggregate produced_qty and rejection by product
        product_production = {}
        product_rejection = {}
        total_produced_qty_month = 0
        for record in data:
            product = record.get('product')
            produced_qty = record.get('produced_qty', 0)
            rejection_qty = record.get('rejection', 0)
            
            if product:
                # Ensure quantities are numeric, treat None as 0
                produced_qty = produced_qty if isinstance(produced_qty, (int, float)) else 0
                rejection_qty = rejection_qty if isinstance(rejection_qty, (int, float)) else 0

                if product not in product_production:
                    product_production[product] = 0
                    product_rejection[product] = 0 # Keep rejection for now, will remove later if not needed.
                product_production[product] += produced_qty
                product_rejection[product] += rejection_qty
                total_produced_qty_month += produced_qty
        
        # Get unique sorted products (keys from either dict, ensuring consistency)
        all_products = sorted(list(set(product_production.keys()).union(set(product_rejection.keys()))))

        # Prepare data for sorting
        product_data_list = []
        for product in all_products:
            produced = product_production.get(product, 0)
            rejected = product_rejection.get(product, 0) # Still keeping rejection_data for now, as it's returned
            
            percentage = 0
            if total_produced_qty_month > 0:
                percentage = (produced / total_produced_qty_month) * 100
            
            product_data_list.append({
                'product': product,
                'produced_qty': produced,
                'rejection_qty': rejected,
                'percentage': percentage # Store as float for sorting
            })

        # Sort the data by percentage in descending order
        product_data_list.sort(key=lambda x: x['percentage'], reverse=True)

        labels = [item['product'] for item in product_data_list]
        quantities = [item['produced_qty'] for item in product_data_list]
        rejection_data = [item['rejection_qty'] for item in product_data_list]
        production_percentage_data = [f"{item['percentage']:.2f}%" for item in product_data_list]

        return labels, quantities, rejection_data, production_percentage_data, total_produced_qty_month

    except Exception as e:
        print(f"Error in get_article_summary_data: {e}")
        return [], [], [], [], 0

def get_available_production_months():
    """Fetches all unique YYYY-MM months from the tab_production table."""
    try:
        response = supabase.table('tab_production').select('date').execute()
        data = response.data

        months = set()
        for record in data:
            record_date_str = record.get('date')
            if record_date_str:
                try:
                    record_date = datetime.strptime(record_date_str, '%Y-%m-%d')
                    months.add(record_date.strftime('%Y-%m'))
                except ValueError:
                    continue
        
        # Sort months in descending order
        sorted_months = sorted(list(months), reverse=True)
        return sorted_months

    except Exception as e:
        print(f"Error in get_available_production_months: {e}")
        return []

def get_monthly_cutting_data():
    """Fetches and aggregates monthly produced_qty from tab_cutting."""
    try:
        response = supabase.table('tab_cutting').select('date, produced_qty').execute()
        data = response.data

        monthly_data = {}
        for record in data:
            record_date_str = record.get('date')
            produced_qty = record.get('produced_qty', 0)
            
            if record_date_str and isinstance(produced_qty, (int, float)):
                try:
                    record_date = datetime.strptime(record_date_str, '%Y-%m-%d')
                    month_key = record_date.strftime('%Y-%m')
                    
                    if month_key not in monthly_data:
                        monthly_data[month_key] = 0
                    monthly_data[month_key] += produced_qty
                except ValueError:
                    continue

        sorted_months = sorted(monthly_data.keys())
        months = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months]
        produced_quantities = [monthly_data[m] for m in sorted_months]
        
        return months, produced_quantities

    except Exception as e:
        print(f"Error in get_monthly_cutting_data: {e}")
        return [], []

def get_available_cutting_months():
    """Fetches all unique YYYY-MM months from the tab_cutting table."""
    try:
        response = supabase.table('tab_cutting').select('date').execute()
        data = response.data

        months = set()
        for record in data:
            record_date_str = record.get('date')
            if record_date_str:
                try:
                    record_date = datetime.strptime(record_date_str, '%Y-%m-%d')
                    months.add(record_date.strftime('%Y-%m'))
                except ValueError:
                    continue
        
        sorted_months = sorted(list(months), reverse=True)
        return sorted_months

    except Exception as e:
        print(f"Error in get_available_cutting_months: {e}")
        return []

def get_article_cutting_summary_data(year_month=None):
    """Fetches and aggregates cutting data by product for a given month, including produced_qty and rejection."""
    try:
        # Assuming 'product' and 'produced_qty' always exist. Checking for 'rejection' column.
        # This query selects produced_qty and rejection. If rejection is not present, it will be None.
        query = supabase.table('tab_cutting').select('product, produced_qty, rejection')
        
        if year_month:
            start_date = f'{year_month}-01'
            year, month = map(int, year_month.split('-'))
            if month == 12:
                end_date = f'{year + 1}-01-01'
            else:
                end_date = f'{year}-{month + 1:02d}-01'
            
            query = query.gte('date', start_date).lt('date', end_date)

        response = query.execute()
        data = response.data

        product_production = {}
        product_rejection = {}
        total_produced_qty_month = 0
        
        for record in data:
            product = record.get('product')
            produced_qty = record.get('produced_qty', 0)
            rejection_qty = record.get('rejection', 0) # Safely get rejection, defaults to 0 if not present
            
            if product:
                produced_qty = produced_qty if isinstance(produced_qty, (int, float)) else 0
                rejection_qty = rejection_qty if isinstance(rejection_qty, (int, float)) else 0

                if product not in product_production:
                    product_production[product] = 0
                    product_rejection[product] = 0
                product_production[product] += produced_qty
                product_rejection[product] += rejection_qty
                total_produced_qty_month += produced_qty
        
        all_products = sorted(list(set(product_production.keys()).union(set(product_rejection.keys()))))

        product_data_list = []
        for product in all_products:
            produced = product_production.get(product, 0)
            rejected = product_rejection.get(product, 0)
            
            percentage = 0
            if total_produced_qty_month > 0:
                percentage = (produced / total_produced_qty_month) * 100
            
            product_data_list.append({
                'product': product,
                'produced_qty': produced,
                'rejection_qty': rejected,
                'percentage': percentage 
            })

        product_data_list.sort(key=lambda x: x['percentage'], reverse=True)

        labels = [item['product'] for item in product_data_list]
        quantities = [item['produced_qty'] for item in product_data_list]
        rejection_data = [item['rejection_qty'] for item in product_data_list]
        production_percentage_data = [f"{item['percentage']:.2f}%" for item in product_data_list]

        return labels, quantities, rejection_data, production_percentage_data, total_produced_qty_month

    except Exception as e:
        print(f"Error in get_article_cutting_summary_data: {e}")
        return [], [], [], [], 0 