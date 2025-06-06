from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
from database import get_db_connection

cutting_bp = Blueprint('cutting', __name__, url_prefix='/cutting')

@cutting_bp.route('/')
def index():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Base query
    query = "SELECT * FROM cutting"
    count_query = "SELECT COUNT(*) FROM cutting"
    params = []
    
    if search:
        query += " WHERE po_no ILIKE %s OR sku ILIKE %s OR product ILIKE %s"
        count_query += " WHERE po_no ILIKE %s OR sku ILIKE %s OR product ILIKE %s"
        search_param = f'%{search}%'
        params = [search_param, search_param, search_param]
    
    # Get total count
    cur.execute(count_query, params)
    total = cur.fetchone()[0]
    
    # Add pagination
    query += " ORDER BY input_timestamp DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])
    
    cur.execute(query, params)
    rows = cur.fetchall()
    
    # Get column names
    headers = [desc[0] for desc in cur.description]
    
    # Convert rows to dictionaries
    data = []
    for row in rows:
        data.append(dict(zip(headers, row)))
    
    cur.close()
    conn.close()
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('cutting.html',
                         headers=headers,
                         rows=data,
                         search=search,
                         page=page,
                         total_pages=total_pages)

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