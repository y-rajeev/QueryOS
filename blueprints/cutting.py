import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
from database import get_db_connection

cutting_bp = Blueprint('cutting', __name__, url_prefix='/cutting')

logger = logging.getLogger(__name__)

@cutting_bp.route('/')
def index():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    conn = None # Initialize conn to None
    cur = None # Initialize cur to None

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Base query
        query = "SELECT * FROM cutting"
        count_query = "SELECT COUNT(*) FROM cutting"
        params = []
        where_clauses = []

        # Handle general search
        if search:
            search_terms = search.split()
            search_conditions = []
            for term in search_terms:
                search_conditions.append("(po_no ILIKE %s OR sku ILIKE %s OR product ILIKE %s)")
                search_param = f'%{term}%'
                params.extend([search_param, search_param, search_param])
            if search_conditions:
                where_clauses.append(f"({" AND ".join(search_conditions)})")

        # Define numeric fields for proper comparison
        numeric_fields = {'pcs_pack', 'sets', 'produced_qty', 'rejection'}

        # Handle filters
        filter_index = 0
        while True:
            field = request.args.get(f'filter_field_{filter_index}')
            operator = request.args.get(f'filter_operator_{filter_index}')
            value = request.args.get(f'filter_value_{filter_index}')

            if not field or not operator:
                break
            
            if operator == 'equal':
                if field in numeric_fields:
                    where_clauses.append(f"{field} = %s")
                    params.append(value)
                else: # Treat as string, use ILIKE for case-insensitive equality
                    where_clauses.append(f"{field} ILIKE %s")
                    params.append(value) # No wildcards here, ILIKE behaves as case-insensitive '='
            elif operator == 'not_equal':
                if field in numeric_fields:
                    where_clauses.append(f"{field} != %s")
                    params.append(value)
                else: # Treat as string, use NOT ILIKE for case-insensitive inequality
                    where_clauses.append(f"{field} NOT ILIKE %s")
                    params.append(value)
            elif operator == 'like':
                where_clauses.append(f"{field} ILIKE %s")
                params.append(f'%{value}%')
            elif operator == 'not_like':
                where_clauses.append(f"{field} NOT ILIKE %s")
                params.append(f'%{value}%')
            elif operator == 'is_set':
                where_clauses.append(f"{field} IS NOT NULL")
            elif operator == 'not_set':
                where_clauses.append(f"{field} IS NULL")
            elif operator == 'gt':
                where_clauses.append(f"{field} > %s")
                params.append(value)
            elif operator == 'lt':
                where_clauses.append(f"{field} < %s")
                params.append(value)
            
            filter_index += 1

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            count_query += " WHERE " + " AND ".join(where_clauses)
    
        print(f"Executing count query: {count_query} with params: {params[:len(params) - 2]}") # Exclude pagination params from logging
        # Get total count
        cur.execute(count_query, params[:len(params) - 2] if len(params) > 2 else params) # Pass parameters without pagination for count query
        total = cur.fetchone()[0]
        
        # Add pagination
        query += " ORDER BY input_timestamp DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        
        print(f"Executing data query: {query} with params: {params}") # Debug print
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Get column names
        headers = [desc[0] for desc in cur.description]
        
        # Convert rows to dictionaries
        data = []
        for row in rows:
            data.append(dict(zip(headers, row)))
        
        total_pages = (total + per_page - 1) // per_page
        
        return render_template('cutting.html',
                            headers=headers,
                            rows=data,
                            search=search,
                            page=page,
                            total_pages=total_pages,
                            current_filters=request.args.to_dict(flat=True))

    except Exception as e:
        logger.error(f"Error fetching cutting data: {str(e)}", exc_info=True)
        flash(f'Error fetching cutting data: {str(e)}', 'error')
        return render_template('cutting.html', headers=[], rows=[], search=search, page=1, total_pages=0, current_filters=request.args.to_dict(flat=True))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@cutting_bp.route('/add', methods=['POST'])
def add():
    try:
        data = request.form
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
        INSERT INTO cutting (
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
        
        cur.execute(query, values)
        conn.commit()
        
        cur.close()
        conn.close()
        
        flash('Cutting data added successfully!', 'success')
        return redirect(url_for('cutting.index'))
        
    except Exception as e:
        flash(f'Error adding cutting data: {str(e)}', 'error')
        return redirect(url_for('cutting.index'))

@cutting_bp.route('/edit/<id>', methods=['POST'])
def edit(id):
    try:
        data = request.form
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
        UPDATE cutting SET
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
        
        cur.execute(query, values)
        conn.commit()
        
        cur.close()
        conn.close()
        
        flash('Cutting data updated successfully!', 'success')
        return redirect(url_for('cutting.index'))
        
    except Exception as e:
        flash(f'Error updating cutting data: {str(e)}', 'error')
        return redirect(url_for('cutting.index'))

@cutting_bp.route('/delete/<id>', methods=['POST'])
def delete(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM cutting WHERE id = %s", (id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        flash('Cutting data deleted successfully!', 'success')
        return redirect(url_for('cutting.index'))
        
    except Exception as e:
        flash(f'Error deleting cutting data: {str(e)}', 'error')
        return redirect(url_for('cutting.index')) 