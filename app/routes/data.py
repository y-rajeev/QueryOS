from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from app.models.data_models import get_paginated_data
from database import get_db_connection
from datetime import datetime, date
import logging
import uuid
import decimal
import csv
import io

logger = logging.getLogger(__name__)

bp = Blueprint('data', __name__)

TABLES = {
    "production": "tab_inprod",
    "cutting": "tab_cutting",
    "tab_production": "tab_production"
}

# Define default limited columns for each table
DEFAULT_LIMITED_COLUMNS = {
    "tab_cutting": ["id", "date", "po_no", "sku", "product", "produced_qty"],
    "tab_inprod": ["id", "po_no", "product", "order_qty", "produced_qty"],
    "tab_production": ["date", "product", "produced_qty"]
}

def get_limited_columns(table_key):
    columns = DEFAULT_LIMITED_COLUMNS.get(table_key)
    print(f"Getting limited columns for {table_key}: {columns}")  # Debug log
    return columns

def get_all_data(table_name: str, search_term: str = "", columns: list[str] = None):
    """
    Fetches all data for a given table, optionally filtered by a search term and limited to specific columns.
    
    Args:
        table_name: The name of the database table.
        search_term: Optional search term to filter results.
        columns: Optional list of column names to select. If None or empty, all columns are selected.
        
    Returns:
        A list of dictionaries, where each dictionary represents a row.
        Includes column names as keys.
    """
    select_columns = ", ".join([f'"{col}"' for col in columns]) if columns else "*"
    base_query = f"SELECT {select_columns} FROM {table_name}"
    params = []
    
    search_term = search_term.strip()
    print(f"[DEBUG] get_all_data - Table: {table_name}, Search Term: '{search_term}', Columns: {columns}") # DEBUG

    # Build dynamic WHERE clause if search term is provided
    if search_term:
        search_conditions = []
        # Common data types that can be searched as text
        searchable_types = ['text', 'varchar', 'char', 'uuid', 'date', 'timestamp', 'timestamp without time zone', 'timestamp with time zone']

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Fetch column names and their data types
                    cur.execute(
                        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s",
                        (table_name,)
                    )
                    columns_info = cur.fetchall()
                    
            for col_name, col_type in columns_info:
                 # Add condition for text-like columns
                 if col_type in searchable_types:
                      search_conditions.append(f'CAST("{col_name}" AS TEXT) ILIKE %s')
                      params.append(f'%{search_term}%')
                 # Add condition for numeric columns if search term looks like a number
                 elif col_type in ('integer', 'smallint', 'bigint', 'decimal', 'numeric', 'real', 'double precision'):
                      # Simple check if search term could be a number (handles integers and decimals)
                      if search_term.replace('.', '', 1).isdigit():
                           search_conditions.append(f'CAST("{col_name}" AS TEXT) ILIKE %s') # Cast numeric to text for LIKE
                           params.append(f'%{search_term}%')

            # Construct the final query
            if search_conditions:
                 query = base_query + " WHERE (" + " OR ".join(search_conditions) + ")"
            else:
                 # If no searchable columns found or search term doesn't match numeric, return base query
                 query = base_query
                 params = [] # Clear params if no conditions were added

        except Exception as e:
             logger.error(f"Error building dynamic search query for table {table_name}: {str(e)}", exc_info=True)
             # Fallback to fetching all data if building the dynamic query fails
             query = base_query
             params = [] # Clear params on failure
    else:
        # No search term, just use the base query
        query = base_query

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Executing query for {table_name} with search '{search_term}': {query} with {len(params)} params.")
                print(f"[DEBUG] get_all_data - Executing SQL: {query}, Params: {params}") # DEBUG
                cur.execute(query, params)
                # Fetch column names
                column_names = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                print(f"[DEBUG] get_all_data - Fetched {len(rows)} rows from database.") # DEBUG
                
                # Convert rows to list of dictionaries
                data = []
                for row in rows:
                     record = dict(zip(column_names, row))
                     # Convert non-JSON serializable types to string for consistency in output
                     for key, value in record.items():
                         if isinstance(value, (datetime, date)):
                             record[key] = value.isoformat() # Use ISO format for dates/datetimes
                         elif isinstance(value, (uuid.UUID, decimal.Decimal)):
                             record[key] = str(value)
                         elif value is None:
                              record[key] = '' # Represent None as empty string in export or display
                     data.append(record)
                print(f"[DEBUG] get_all_data - Returning {len(data)} processed rows.") # DEBUG
                return data
                
    except Exception as e:
        logger.error(f"Error fetching all data for table {table_name} with search '{search_term}': {str(e)}", exc_info=True)
        print(f"[DEBUG] get_all_data - Error: {e}") # DEBUG
        return [] # Return empty list on error

@bp.route("/production")
def production_data():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 20))
    column_view = request.args.get("column_view", "all")
    print(f"Production page - Column view: {column_view}")  # Debug log
    
    columns_to_fetch = get_limited_columns("tab_inprod") if column_view == "limited" else None
    print(f"Production page - Columns to fetch: {columns_to_fetch}")  # Debug log
    
    data = get_paginated_data(TABLES["production"], search, page, limit, columns=columns_to_fetch)
    print(f"Production page - Headers: {data.get('headers')}")  # Debug log
    return render_template("shipment.html", **data, column_view=column_view)

@bp.route("/cutting")
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
    print(f"Cutting page - Headers: {data.get('headers')}")  # Debug log
    return render_template("cutting.html", **data, column_view=column_view)

@bp.route("/cutting/details/test", methods=['GET'])
def cutting_details_test():
    logger.info("Temporary cutting details test route hit.")
    return jsonify({"message": "Test route successful!"}), 200

@bp.route("/cutting/details/<string:record_id>", methods=['GET'])
def get_cutting_details(record_id):
    """
    Fetches full details for a single cutting record.
    """
    query = "SELECT * FROM tab_cutting WHERE id = %s"
    try:
        logger.info(f"Attempting to fetch details for record ID: {record_id}")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (record_id,))
                row = cur.fetchone()
                if not row:
                    logger.warning(f"Record with ID {record_id} not found during re-fetch.")
                    return jsonify({'message': 'Record not found'}), 404

                column_names = [desc[0] for desc in cur.description]
                record_details = dict(zip(column_names, row))

                # Convert non-JSON serializable types to string
                for key, value in record_details.items():
                    if isinstance(value, (datetime, date)):
                        record_details[key] = value.isoformat() # Use ISO format for dates/datetimes
                    elif isinstance(value, (uuid.UUID, decimal.Decimal)):
                        record_details[key] = str(value)
                    # Add other types here if necessary

                logger.info(f"Successfully fetched details for record ID: {record_id}")
                return jsonify(record_details)

    except Exception as e:
        logger.error(f"Error fetching cutting record details for ID {record_id}: {str(e)}", exc_info=True)
        return jsonify({'message': 'Internal Server Error'}), 500

@bp.route("/cutting/add", methods=['POST'])
def add_cutting():
    try:
        data = request.form
        # Use the execute_query helper for insert
        query = """
        INSERT INTO tab_cutting (
            id, input_timestamp, date, po_no, sku, product,
            line, design, size, pcs_pack, sets,
            produced_qty, unpair_pcs, rejection
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        values = (
            data.get('id'),
            datetime.now(),
            data.get('date'),
            data.get('po_no'),
            data.get('sku'),
            data.get('product'),
            data.get('line'),
            data.get('design'),
            data.get('size'),
            data.get('pcs_pack'),
            data.get('sets'),
            data.get('produced_qty'),
            data.get('unpair_pcs'),
            data.get('rejection')
        )

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                conn.commit()
        
        logger.info("Successfully added new cutting record.")
        flash('Cutting data added successfully!', 'success')
        return redirect(url_for('data.cutting'))

    except Exception as e:
        logger.error(f"Error adding cutting data: {str(e)}", exc_info=True)
        flash(f'Error adding cutting data: {str(e)}', 'error')
        return redirect(url_for('data.cutting'))

@bp.route("/cutting/edit/<string:id>", methods=['POST'])
def edit_cutting(id):
    try:
        data = request.form
        # Use explicit cursor for update
        query = """
        UPDATE tab_cutting SET
            date = %s,
            po_no = %s,
            sku = %s,
            product = %s,
            line = %s,
            design = %s,
            size = %s,
            pcs_pack = %s,
            sets = %s,
            produced_qty = %s,
            unpair_pcs = %s,
            rejection = %s
        WHERE id = %s
        """

        values = (
            data.get('date'),
            data.get('po_no'),
            data.get('sku'),
            data.get('product'),
            data.get('line'),
            data.get('design'),
            data.get('size'),
            data.get('pcs_pack'),
            data.get('sets'),
            data.get('produced_qty'),
            data.get('unpair_pcs'),
            data.get('rejection'),
            id
        )

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                conn.commit()

        logger.info(f"Successfully updated cutting record with ID: {id}")
        flash('Cutting data updated successfully!', 'success')
        return redirect(url_for('data.cutting'))

    except Exception as e:
        logger.error(f"Error updating cutting data for ID {id}: {str(e)}", exc_info=True)
        flash(f'Error updating cutting data: {str(e)}', 'error')
        return redirect(url_for('data.cutting'))

@bp.route("/cutting/bulk_delete", methods=['POST'])
def bulk_delete_cutting():
    """
    Deletes multiple cutting records based on a list of IDs.
    """
    try:
        data = request.get_json()
        ids_to_delete = data.get('ids', [])

        if not ids_to_delete:
            logger.warning("Bulk delete request received with no IDs.")
            return jsonify({'message': 'No IDs provided for deletion'}), 400

        # Use a parameterized query with ANY for the list of IDs
        query = "DELETE FROM tab_cutting WHERE id = ANY(%s)"

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (ids_to_delete,))
                deleted_count = cur.rowcount
                conn.commit()

        logger.info(f"Bulk deleted {deleted_count} cutting records.")
        return jsonify({'message': f'{deleted_count} records deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error during bulk cutting data deletion: {str(e)}", exc_info=True)
        return jsonify({'message': f'Error deleting records: {str(e)}'}), 500

@bp.route("/tab-production")
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
    return render_template("tab_production.html", **data, column_view=column_view)

@bp.route("/cutting/export", methods=['GET'])
def export_cutting():
    search = request.args.get("search", "").strip()
    print(f"[DEBUG] export_cutting - Received request for search: '{search}'") # DEBUG
    data = get_all_data(TABLES["cutting"], search)
    print(f"[DEBUG] export_cutting - Data received from get_all_data: {len(data)} rows.") # DEBUG
    if not data:
        flash("No data to export.", "warning")
        return redirect(url_for('data.cutting'))

    si = io.StringIO()
    cw = csv.writer(si)

    headers = list(data[0].keys()) if data else [] # Ensure headers are a list
    cw.writerow(headers)

    for row in data:
        cw.writerow([row.get(col, '') for col in headers]) # Use .get to handle missing keys gracefully

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={TABLES['cutting']}_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@bp.route("/production/export", methods=['GET'])
def export_production():
    search = request.args.get("search", "").strip()
    print(f"[DEBUG] export_production - Received request for search: '{search}'") # DEBUG
    data = get_all_data(TABLES["production"], search)
    print(f"[DEBUG] export_production - Data received from get_all_data: {len(data)} rows.") # DEBUG
    if not data:
        flash("No data to export.", "warning")
        return redirect(url_for('data.production_data'))

    si = io.StringIO()
    cw = csv.writer(si)

    headers = list(data[0].keys()) if data else [] # Ensure headers are a list
    cw.writerow(headers)

    for row in data:
        cw.writerow([row.get(col, '') for col in headers]) # Use .get to handle missing keys gracefully

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={TABLES['production']}_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@bp.route("/tab-production/export", methods=['GET'])
def export_tab_production():
    search = request.args.get("search", "").strip()
    print(f"[DEBUG] export_tab_production - Received request for search: '{search}'") # DEBUG
    data = get_all_data(TABLES["tab_production"], search)
    print(f"[DEBUG] export_tab_production - Data received from get_all_data: {len(data)} rows.") # DEBUG
    if not data:
        flash("No data to export.", "warning")
        return redirect(url_for('data.tab_production'))

    si = io.StringIO()
    cw = csv.writer(si)

    headers = list(data[0].keys()) if data else [] # Ensure headers are a list
    cw.writerow(headers)

    for row in data:
        cw.writerow([row.get(col, '') for col in headers]) # Use .get to handle missing keys gracefully

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={TABLES['tab_production']}_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output 