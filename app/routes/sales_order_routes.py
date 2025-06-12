from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import uuid
from app.utils.supabase_client import get_supabase_client
from app.utils.auth import login_required

bp = Blueprint('sales_order', __name__, url_prefix='/sales-order')

@bp.route('/')
@login_required
def list_orders():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    # Get filter parameters
    po_no = request.args.get('po_no', '')
    status = request.args.get('status', '')
    branch = request.args.get('branch', '')
    
    # Build query
    query = get_supabase_client().table('tab_sales_order').select('*')
    
    # Apply filters
    if po_no:
        query = query.ilike('po_no', f'%{po_no}%')
    if status:
        query = query.eq('status', status)
    if branch:
        query = query.eq('branch', branch)
    
    # Get total count for pagination
    count_result = get_supabase_client().table('tab_sales_order').select('*', count='exact')
    if po_no:
        count_result = count_result.ilike('po_no', f'%{po_no}%')
    if status:
        count_result = count_result.eq('status', status)
    if branch:
        count_result = count_result.eq('branch', branch)
    
    count_data = count_result.execute()
    total_count = count_data.count if hasattr(count_data, 'count') else 0
    
    # Get paginated results
    result = query.range(offset, offset + per_page - 1).execute()
    orders = result.data
    
    # Get unique values for filter dropdowns
    all_statuses_data = get_supabase_client().table('tab_sales_order').select('status').execute().data
    statuses = list(set(s['status'] for s in all_statuses_data if s['status'])) if all_statuses_data else []
    
    all_branches_data = get_supabase_client().table('tab_sales_order').select('branch').execute().data
    branches = list(set(b['branch'] for b in all_branches_data if b['branch'])) if all_branches_data else []
    
    return render_template('sales_order/sales_order_list.html',
                         orders=orders,
                         page=page,
                         per_page=per_page,
                         total_count=total_count,
                         po_no=po_no,
                         status=status,
                         branch=branch,
                         statuses=statuses,
                         branches=branches)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        try:
            # Get form data
            data = {
                'po_no': request.form['po_no'],
                'po_date': request.form['po_date'],
                'delivery_date': request.form['delivery_date'],
                'branch': request.form['branch'],
                'warehouse': request.form['warehouse'],
                'status': request.form['status'],
                'repository': request.form['repository'],
                'country': request.form['country'],
                'mode': request.form['mode'],
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Check if PO number already exists
            existing = get_supabase_client().table('tab_sales_order').select('po_no').eq('po_no', data['po_no']).execute()
            if existing.data:
                flash('PO number already exists!', 'error')
                return render_template('sales_order/sales_order_form.html', data=data, items=[])
            
            # Insert parent record
            result = get_supabase_client().table('tab_sales_order').insert(data).execute()
            
            # Process child items
            items = []
            total_qty = 0
            for i in range(int(request.form['item_count'])):
                item = {
                    'id': str(uuid.uuid4()),
                    'sr_no': i + 1,
                    'po_no': data['po_no'],
                    'sku': request.form.get(f'items[{i}][sku]'),
                    'product': request.form.get(f'items[{i}][product]'),
                    'category': request.form.get(f'items[{i}][category]'),
                    'line': request.form.get(f'items[{i}][line]'),
                    'design': request.form.get(f'items[{i}][design]'),
                    'size': request.form.get(f'items[{i}][size]'),
                    'pack_of': request.form.get(f'items[{i}][pack_of]'),
                    'sets': request.form.get(f'items[{i}][sets]'),
                    'pieces': request.form.get(f'items[{i}][pieces]'),
                    'created_at': datetime.utcnow().isoformat()
                }
                items.append(item)
                total_qty += int(item['pieces'] or 0)
            
            # Insert child records
            if items:
                get_supabase_client().table('tab_sales_order_items').insert(items).execute()
            
            # Update total quantity
            get_supabase_client().table('tab_sales_order').update({'total_qty': total_qty}).eq('po_no', data['po_no']).execute()
            
            flash('Sales order created successfully!', 'success')
            return redirect(url_for('sales_order.list_orders'))
            
        except Exception as e:
            flash(f'Error creating sales order: {str(e)}', 'error')
            return render_template('sales_order/sales_order_form.html', data=data, items=[])
    
    # For GET request (new form)
    empty_data = {
        "po_no": "",
        "po_date": "",
        "delivery_date": "",
        "total_qty": "",
        "branch": "",
        "warehouse": "",
        "status": "",
        "repository": "",
        "country": "",
        "mode": ""
    }
    return render_template('sales_order/sales_order_form.html', data=empty_data, items=[])

@bp.route('/<po_no>/edit', methods=['GET', 'POST'])
@login_required
def edit_order(po_no):
    if request.method == 'POST':
        try:
            # Get form data
            data = {
                'po_date': request.form['po_date'],
                'delivery_date': request.form['delivery_date'],
                'branch': request.form['branch'],
                'warehouse': request.form['warehouse'],
                'status': request.form['status'],
                'repository': request.form['repository'],
                'country': request.form['country'],
                'mode': request.form['mode']
            }
            
            # Update parent record
            get_supabase_client().table('tab_sales_order').update(data).eq('po_no', po_no).execute()
            
            # Delete existing items
            get_supabase_client().table('tab_sales_order_items').delete().eq('po_no', po_no).execute()
            
            # Process new items
            items = []
            total_qty = 0
            for i in range(int(request.form['item_count'])):
                item = {
                    'id': str(uuid.uuid4()),
                    'sr_no': i + 1,
                    'po_no': po_no,
                    'sku': request.form.get(f'items[{i}][sku]'),
                    'product': request.form.get(f'items[{i}][product]'),
                    'category': request.form.get(f'items[{i}][category]'),
                    'line': request.form.get(f'items[{i}][line]'),
                    'design': request.form.get(f'items[{i}][design]'),
                    'size': request.form.get(f'items[{i}][size]'),
                    'pack_of': request.form.get(f'items[{i}][pack_of]'),
                    'sets': request.form.get(f'items[{i}][sets]'),
                    'pieces': request.form.get(f'items[{i}][pieces]'),
                    'created_at': datetime.utcnow().isoformat()
                }
                items.append(item)
                total_qty += int(item['pieces'] or 0)
            
            # Insert new items
            if items:
                get_supabase_client().table('tab_sales_order_items').insert(items).execute()
            
            # Update total quantity
            get_supabase_client().table('tab_sales_order').update({'total_qty': total_qty}).eq('po_no', po_no).execute()
            
            flash('Sales order updated successfully!', 'success')
            return redirect(url_for('sales_order.list_orders'))
            
        except Exception as e:
            flash(f'Error updating sales order: {str(e)}', 'error')
            return render_template('sales_order/sales_order_form.html', data=data)
    
    # Get existing order data
    order = get_supabase_client().table('tab_sales_order').select('*').eq('po_no', po_no).execute().data[0]
    items = get_supabase_client().table('tab_sales_order_items').select('*').eq('po_no', po_no).execute().data
    
    return render_template('sales_order/sales_order_form.html', data=order, items=items)

@bp.route('/<po_no>/view')
@login_required
def view_order(po_no):
    order = get_supabase_client().table('tab_sales_order').select('*').eq('po_no', po_no).execute().data[0]
    items = get_supabase_client().table('tab_sales_order_items').select('*').eq('po_no', po_no).execute().data
    
    return render_template('sales_order/sales_order_detail.html', order=order, items=items)

@bp.route('/<po_no>/delete', methods=['POST'])
@login_required
def delete_order(po_no):
    try:
        # Delete child records first
        get_supabase_client().table('tab_sales_order_items').delete().eq('po_no', po_no).execute()
        # Delete parent record
        get_supabase_client().table('tab_sales_order').delete().eq('po_no', po_no).execute()
        
        flash('Sales order deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting sales order: {str(e)}', 'error')
    
    return redirect(url_for('sales_order.list_orders')) 