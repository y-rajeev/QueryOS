from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from app.models.data_models import get_paginated_data, add_cutting_record, update_cutting_record, delete_cutting_records, supabase, get_cutting_summary_metrics
from datetime import datetime, date
import logging
import uuid
import decimal
import csv
import io

logger = logging.getLogger(__name__)

bp = Blueprint('data', __name__)

TABLES = {
    "shipment": "tab_inprod",
    "cutting": "tab_cutting",
    "tab_production": "tab_production"
}

# Define default limited columns for each table
DEFAULT_LIMITED_COLUMNS = {
    "tab_cutting": ["id", "date", "po_no", "sku", "product", "produced_qty"],
    "tab_inprod": ["id", "po_no", "product", "order_qty", "produced_qty"],
    "tab_production": ["date", "product", "pcs_pack", "sets", "produced_qty", "unpair_pcs"]
}

def get_limited_columns(table_key):
    columns = DEFAULT_LIMITED_COLUMNS.get(table_key)
    print(f"Getting limited columns for {table_key}: {columns}")  # Debug log
    return columns

def get_all_data(table_name: str, search_term: str = "", columns: list[str] = None):
    """
    Fetches all data for a given table, optionally filtered by a search term and limited to specific columns.
    Now uses Supabase client directly.
    
    Args:
        table_name: The name of the database table.
        search_term: Optional search term to filter results.
        columns: Optional list of column names to select. If None or empty, all columns are selected.
        
    Returns:
        A list of dictionaries, where each dictionary represents a row.
        Includes column names as keys.
    """
    select_columns = ",".join(columns) if columns else "*"
    
    search_term = search_term.strip()
    print(f"[DEBUG] get_all_data - Table: {table_name}, Search Term: '{search_term}', Columns: {columns}")

    try:
        query = supabase.table(table_name).select(select_columns)
        
        if search_term:
            # If specific columns are provided by the caller, use those for the search.
            # Otherwise, fall back to a broader set of common text-based columns.
            if columns:
                # Filter out explicitly known non-string/non-searchable columns from the provided list
                # This list should be expanded if there are other numeric/boolean/date fields in your tables
                non_searchable_types = ['id', 'date', 'input_timestamp', 'created_at', 'produced_qty', 'rejection', 'pcs_pack', 'sets', 'unpair_pcs', 'po_qty', 'dispatched_qty', 'pending_qty', 'order_qty']
                searchable_cols = [col for col in columns if col not in non_searchable_types]
            else:
                # Fallback to a broader set of common text-based columns for generic search if no specific columns were provided
                searchable_cols = ['po_no', 'sku', 'product', 'design', 'line', 'shipment_id', 'channel_abb', 'customer_name', 'status', 'production', 'mode']

            conditions = []
            for col in searchable_cols:
                conditions.append(f"{col}.ilike.%{search_term}%")
            
            if conditions:
                print(f"[DEBUG] Constructing Supabase OR query for table '{table_name}' with conditions: {",".join(conditions)}")
                query = query.or_(",".join(conditions))
            else:
                print(f"[DEBUG] No valid searchable columns found for table '{table_name}' with query '{search_term}' from provided columns: {columns}")

        # No dynamic WHERE clause based on `information_schema.columns` needed here for Supabase

        # Handle individual column filters (already implemented in get_paginated_data)
        # This part will be handled by get_paginated_data or need to be adapted if this was a standalone function.
        # For now, let's simplify get_all_data to just fetch, as get_paginated_data already does filtering.

        data_response = query.execute()
        rows = data_response.data
        print(f"[DEBUG] get_all_data - Fetched {len(rows)} rows from Supabase.")
        return rows
                
    except Exception as e:
        logger.error(f"Error fetching all data for table {table_name} with search '{search_term}' from Supabase: {str(e)}", exc_info=True)
        print(f"[DEBUG] get_all_data - Error: {e}")
        return [] # Return empty list on error

@bp.route("/pending-order")
def production_data():
    try:
        # Define the columns we want to show in order
        columns = [
            'shipment_id',
            'date',
            'ETD',
            'production',
            'channel_abb',
            'mode',
            'po_qty',
            'dispatched_qty',
            'pending_qty',
            'status'
        ]
        
        # Build the query
        query = supabase.table('pending_order').select(','.join(columns))
        
        # Add sorting by date descending
        query = query.order('date', desc=True)
        
        # Execute query
        response = query.execute()
        
        # Process the response
        if response.data:
            orders = response.data
            total_records = len(orders)
        else:
            orders = []
            total_records = 0
        
        return render_template(
            "shipment.html",
            headers=columns,
            orders=orders,
            total_records=total_records
        )
        
    except Exception as e:
        logger.error(f"Error fetching pending order data: {str(e)}", exc_info=True)
        flash(f'Error loading pending orders: {str(e)}', 'error')
        return render_template(
            "shipment.html",
            headers=[],
            orders=[],
            total_records=0
        )

@bp.route("/cutting-phase")
def cutting():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 20))
    column_view = request.args.get("column_view", "all")
    print(f"Cutting page - Column view: {column_view}")  # Debug log
    
    columns_to_fetch = get_limited_columns("tab_cutting") if column_view == "limited" else None
    print(f"Cutting page - Columns to fetch: {columns_to_fetch}")  # Debug log
    
    data = get_paginated_data(TABLES["cutting"], search, page, limit, columns=columns_to_fetch)

    # Fetch summary metrics
    summary_metrics = get_cutting_summary_metrics()
    
    print(f"Cutting page - Headers: {data.get('headers')}")  # Debug log
    return render_template("manufacturing/cutting_phase.html", **data, column_view=column_view, today_date=date.today().isoformat(), summary_metrics=summary_metrics)

@bp.route("/cutting-phase/details/test", methods=['GET'])
def cutting_details_test():
    logger.info("Temporary cutting details test route hit.")
    return jsonify({"message": "Test route successful!"}), 200

@bp.route("/cutting-phase/details/<string:record_id>", methods=['GET'])
def get_cutting_details(record_id):
    """
    Fetches full details for a single cutting record using Supabase.
    """
    try:
        logger.info(f"Attempting to fetch details for record ID: {record_id} from Supabase.")
        response = supabase.table('tab_cutting').select('*').eq('id', record_id).execute()
        if response.data:
            record_details = response.data[0]
            logger.info(f"Successfully fetched details for record ID: {record_id} from Supabase.")
            return jsonify(record_details)
        else:
            logger.warning(f"Record with ID {record_id} not found in Supabase: {response.count}")
            return jsonify({'message': 'Record not found'}), 404

    except Exception as e:
        logger.error(f"Error fetching cutting record details for ID {record_id} from Supabase: {str(e)}", exc_info=True)
        return jsonify({'message': 'Internal Server Error'}), 500

@bp.route("/cutting-phase/add", methods=['POST'])
def add_cutting():
    try:
        data = request.form

        # 1. Automatic ID generation (handled in data_models.py now, but kept for clarity if needed here)
        record_id = str(uuid.uuid4()) # Generate a new UUID if you want to explicitly pass it

        # 2. Date: Use today's date if not provided
        date_str = data.get('date')
        if date_str:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            record_date = date.today()

        pcs_pack = int(data.get('pcs_pack')) if data.get('pcs_pack') else 0
        produced_qty = int(data.get('produced_qty')) if data.get('produced_qty') else 0
        rejection = int(data.get('rejection')) if data.get('rejection') else 0

        # 3. Calculate Sets and Unpair PCS
        if pcs_pack > 0:
            calculated_sets = produced_qty // pcs_pack
            calculated_unpair_pcs = produced_qty % pcs_pack
        else:
            calculated_sets = 0
            calculated_unpair_pcs = produced_qty

        new_record = {
            "id": record_id,
            "input_timestamp": datetime.now().isoformat(), # Convert datetime to ISO string
            "date": record_date.isoformat(), # Convert date to ISO string
            "po_no": data.get('po_no'),
            "sku": data.get('sku'),
            "product": data.get('product'),
            "line": data.get('line'),
            "design": data.get('design'),
            "size": data.get('size'),
            "pcs_pack": pcs_pack,
            "sets": calculated_sets,
            "produced_qty": produced_qty,
            "unpair_pcs": calculated_unpair_pcs,
            "rejection": rejection
        }

        added_record = add_cutting_record(new_record)
        
        logger.info(f"Successfully added new cutting record with ID: {added_record.get('id')}")
        flash('Cutting data added successfully!', 'success')
        return redirect(url_for('data.cutting'))

    except Exception as e:
        logger.error(f"Error adding cutting data to Supabase: {str(e)}", exc_info=True)
        flash(f'Error adding cutting data: {str(e)}', 'error')
        return redirect(url_for('data.cutting'))

@bp.route("/cutting-phase/edit/<string:id>", methods=['GET', 'POST'])
def edit_cutting(id):
    if request.method == 'POST':
        try:
            data = request.form

            pcs_pack = int(data.get('pcs_pack')) if data.get('pcs_pack') else 0
            produced_qty = int(data.get('produced_qty')) if data.get('produced_qty') else 0
            rejection = int(data.get('rejection')) if data.get('rejection') else 0

            # Calculate Sets and Unpair PCS
            if pcs_pack > 0:
                calculated_sets = produced_qty // pcs_pack
                calculated_unpair_pcs = produced_qty % pcs_pack
            else:
                calculated_sets = 0
                calculated_unpair_pcs = produced_qty

            updated_record_data = {
                "date": datetime.strptime(data.get('date'), '%Y-%m-%d').date(),
                "po_no": data.get('po_no'),
                "sku": data.get('sku'),
                "product": data.get('product'),
                "line": data.get('line'),
                "design": data.get('design'),
                "size": data.get('size'),
                "pcs_pack": pcs_pack,
                "sets": calculated_sets,
                "produced_qty": produced_qty,
                "unpair_pcs": calculated_unpair_pcs,
                "rejection": rejection
            }

            updated_record = update_cutting_record(id, updated_record_data)
            
            flash('Cutting data updated successfully!', 'success')
            return redirect(url_for('data.cutting'))

        except Exception as e:
            logger.error(f"Error editing cutting data in Supabase: {str(e)}", exc_info=True)
            flash(f'Error editing cutting data: {str(e)}', 'error')
            return redirect(url_for('data.cutting'))
    
    else: # GET request for edit_cutting
        record = None
        try:
            response = supabase.table('tab_cutting').select('*').eq('id', id).execute()
            if response.data:
                record = response.data[0]
                # Format date for HTML input
                if 'date' in record:
                    # Convert Supabase date string (e.g., '2023-10-27') to 'YYYY-MM-DD' for HTML date input
                    record['date'] = record['date'].split('T')[0] if 'T' in record['date'] else record['date']
            else:
                flash('Record not found.', 'error')
                return redirect(url_for('data.cutting'))
        except Exception as e:
            logger.error(f"Error fetching record for edit from Supabase: {str(e)}", exc_info=True)
            flash(f'Error fetching record for edit: {str(e)}', 'error')
            return redirect(url_for('data.cutting'))

        return render_template('components/edit_cutting_modal_content.html', record=record)

@bp.route("/cutting-phase/bulk_delete", methods=['POST'])
def bulk_delete_cutting():
    selected_ids = request.json.get('ids', [])
    if not selected_ids:
        return jsonify({'message': 'No records selected for deletion.'}), 400

    try:
        # Supabase delete function will handle validation if IDs are not found
        deleted_count = delete_cutting_records(selected_ids)
        
        flash(f'{deleted_count} records deleted successfully!', 'success')
        return jsonify({'message': 'Records deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error during bulk delete from Supabase: {str(e)}", exc_info=True)
        return jsonify({'message': f'Error deleting records: {str(e)}'}), 500

@bp.route("/production-phase")
def tab_production():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 20))
    column_view = request.args.get("column_view", "all")
    print(f"Tab Production page - Column view: {column_view}")  # Debug log
    
    columns_to_fetch = get_limited_columns("tab_production") if column_view == "limited" else None
    print(f"Tab Production page - Columns to fetch: {columns_to_fetch}")  # Debug log
    
    data = get_paginated_data(TABLES["tab_production"], search, page, limit, columns=columns_to_fetch)
    print(f"Tab Production page - Headers: {data.get('headers')}")  # Debug log
    return render_template("manufacturing/production_phase.html", **data, column_view=column_view, today_date=date.today().isoformat())

@bp.route("/production-phase/details/<string:record_id>", methods=['GET'])
def get_production_details(record_id):
    """
    Fetches full details for a single production record using Supabase.
    """
    try:
        logger.info(f"Attempting to fetch details for record ID: {record_id} from Supabase.")
        response = supabase.table('tab_production').select('*').eq('id', record_id).execute()
        if response.data:
            record_details = response.data[0]
            logger.info(f"Successfully fetched details for record ID: {record_id} from Supabase.")
            return jsonify(record_details)
        else:
            logger.warning(f"Record with ID {record_id} not found in Supabase: {response.count}")
            return jsonify({'message': 'Record not found'}), 404

    except Exception as e:
        logger.error(f"Error fetching production record details for ID {record_id} from Supabase: {str(e)}", exc_info=True)
        return jsonify({'message': 'Internal Server Error'}), 500

@bp.route("/production-phase/add", methods=['POST'])
def add_production():
    try:
        data = request.form
        record_id = str(uuid.uuid4())

        # Date: Use today's date if not provided
        date_str = data.get('date')
        if date_str:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            record_date = date.today()

        produced_qty = int(data.get('produced_qty')) if data.get('produced_qty') else 0
        rejection = int(data.get('rejection')) if data.get('rejection') else 0
        
        # Retrieve pcs_pack and calculate sets and unpair_pcs
        pcs_pack = int(data.get('pcs_pack')) if data.get('pcs_pack') else 0
        
        calculated_sets = 0
        calculated_unpair_pcs = 0
        if pcs_pack > 0:
            calculated_sets = produced_qty // pcs_pack
            calculated_unpair_pcs = produced_qty % pcs_pack
        else:
            # If pcs_pack is 0, sets should be 0 and unpair_pcs should be the full produced_qty
            calculated_unpair_pcs = produced_qty

        new_record = {
            "id": record_id,
            "input_timestamp": datetime.now().isoformat(),
            "date": record_date.isoformat(),
            "po_no": data.get('po_no'),
            "sku": data.get('sku'),
            "product": data.get('product'),
            "line": data.get('line'),
            "design": data.get('design'),
            "size": data.get('size'),
            "pcs_pack": pcs_pack,
            "sets": calculated_sets,
            "produced_qty": produced_qty,
            "unpair_pcs": calculated_unpair_pcs,
            "rejection": rejection
        }

        response = supabase.table('tab_production').insert(new_record).execute()
        if response.data:
            flash('Production data added successfully!', 'success')
        else:
            raise Exception("Failed to add record: No response data from Supabase")
        
        return redirect(url_for('data.tab_production'))

    except Exception as e:
        logger.error(f"Error adding production data to Supabase: {str(e)}", exc_info=True)
        flash(f'Error adding production data: {str(e)}', 'error')
        return redirect(url_for('data.tab_production'))

@bp.route("/production-phase/edit/<string:id>", methods=['GET', 'POST'])
def edit_production(id):
    if request.method == 'POST':
        try:
            data = request.form
            produced_qty = int(data.get('produced_qty')) if data.get('produced_qty') else 0
            rejection = int(data.get('rejection')) if data.get('rejection') else 0
            
            # Retrieve pcs_pack and calculate sets and unpair_pcs for edit
            pcs_pack = int(data.get('pcs_pack')) if data.get('pcs_pack') else 0
            
            calculated_sets = 0
            calculated_unpair_pcs = 0
            if pcs_pack > 0:
                calculated_sets = produced_qty // pcs_pack
                calculated_unpair_pcs = produced_qty % pcs_pack
            else:
                calculated_unpair_pcs = produced_qty

            updated_record_data = {
                "date": datetime.strptime(data.get('date'), '%Y-%m-%d').date().isoformat(),
                "po_no": data.get('po_no'),
                "sku": data.get('sku'),
                "product": data.get('product'),
                "line": data.get('line'),
                "design": data.get('design'),
                "size": data.get('size'),
                "pcs_pack": pcs_pack,
                "sets": calculated_sets,
                "produced_qty": produced_qty,
                "unpair_pcs": calculated_unpair_pcs,
                "rejection": rejection
            }

            response = supabase.table('tab_production').update(updated_record_data).eq('id', id).execute()
            if response.data:
                flash('Production data updated successfully!', 'success')
            else:
                raise Exception("Failed to update record: No response data from Supabase")
            
            return redirect(url_for('data.tab_production'))

        except Exception as e:
            logger.error(f"Error editing production data in Supabase: {str(e)}", exc_info=True)
            flash(f'Error editing production data: {str(e)}', 'error')
            return redirect(url_for('data.tab_production'))
    
    else: # GET request for edit_production
        record = None
        try:
            response = supabase.table('tab_production').select('*').eq('id', id).execute()
            if response.data:
                record = response.data[0]
                # Format date for HTML input
                if 'date' in record:
                    record['date'] = record['date'].split('T')[0] if 'T' in record['date'] else record['date']
            else:
                flash('Record not found.', 'error')
                return redirect(url_for('data.tab_production'))
        except Exception as e:
            logger.error(f"Error fetching record for edit from Supabase: {str(e)}", exc_info=True)
            flash(f'Error fetching record for edit: {str(e)}', 'error')
            return redirect(url_for('data.tab_production'))

        return render_template('components/edit_production_modal_content.html', record=record)

@bp.route("/production-phase/bulk_delete", methods=['POST'])
def bulk_delete_production():
    selected_ids = request.json.get('ids', [])
    if not selected_ids:
        return jsonify({'message': 'No records selected for deletion.'}), 400

    try:
        response = supabase.table('tab_production').delete().in_('id', selected_ids).execute()
        if response.data is not None:
            deleted_count = len(response.data)
            flash(f'{deleted_count} records deleted successfully!', 'success')
            return jsonify({'message': 'Records deleted successfully'}), 200
        else:
            raise Exception("Failed to delete records: No response data from Supabase")

    except Exception as e:
        logger.error(f"Error during bulk delete from Supabase: {str(e)}", exc_info=True)
        return jsonify({'message': f'Error deleting records: {str(e)}'}), 500

@bp.route("/cutting-phase/export", methods=['GET'])
def export_cutting():
    search = request.args.get("search", "")
    
    # Fetch all data (not paginated) for export using Supabase
    data_rows = get_all_data(TABLES["cutting"], search_term=search, columns=None) # get_all_data now uses Supabase

    if not data_rows:
        flash('No data to export.', 'info')
        return redirect(url_for('data.cutting'))

    # Create a CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)

    # Write headers
    headers = data_rows[0].keys()
    cw.writerow(headers)

    # Write data rows
    for row in data_rows:
        cw.writerow([row[key] for key in headers])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=Daily Cutting.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@bp.route("/pending-order/export", methods=['GET'])
def export_production():
    search = request.args.get("search", "")
    data_rows = get_all_data(TABLES["shipment"], search_term=search, columns=None) # get_all_data now uses Supabase

    if not data_rows:
        flash('No data to export.', 'info')
        return redirect(url_for('data.production_data'))
    
    si = io.StringIO()
    cw = csv.writer(si)
    headers = data_rows[0].keys()
    cw.writerow(headers)
    for row in data_rows:
        cw.writerow([row[key] for key in headers])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=production_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@bp.route("/production-phase/export", methods=['GET'])
def export_tab_production():
    search = request.args.get("search", "")
    data_rows = get_all_data(TABLES["tab_production"], search_term=search, columns=None) # get_all_data now uses Supabase

    if not data_rows:
        flash('No data to export.', 'info')
        return redirect(url_for('data.tab_production'))

    si = io.StringIO()
    cw = csv.writer(si)
    headers = data_rows[0].keys()
    cw.writerow(headers)
    for row in data_rows:
        cw.writerow([row[key] for key in headers])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=Production Data.csv"
    output.headers["Content-type"] = "text/csv"
    return output 