from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
from app import User
from app.models.data_models import get_monthly_production_data, get_available_production_months, get_article_summary_data, get_monthly_cutting_data, get_available_cutting_months, get_article_cutting_summary_data, get_cutting_summary_metrics, get_production_summary_metrics
from app.routes.data import get_all_data

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    # For now, automatically log in a test user
    if not current_user.is_authenticated:
        user = User('test_user')
        login_user(user)
    return render_template('dashboard.html')

@bp.route('/reports')
@login_required
def reports():
    return render_template('reports/reports_dashboard.html')

@bp.route('/search')
@login_required
def search_results():
    query = request.args.get('search', '').strip().lower()
    
    # --- Page Search / Redirect Logic ---
    if "sales order" in query:
        return redirect(url_for('sales_order.list_orders'))
    elif "production phase" in query or "production data" in query:
        return redirect(url_for('data.tab_production'))
    elif "cutting phase" in query or "cutting data" in query:
        return redirect(url_for('data.cutting'))
    elif "pending order" in query or "dispatch data" in query:
        return redirect(url_for('data.production_data')) # Assuming production_data route handles pending orders
    # --- End Page Search / Redirect Logic ---

    # If no direct page match, proceed with content search (existing logic)
    production_results = []
    cutting_results = []
    sales_order_results = []
    pending_order_results = []

    if query:
        # Define columns to search for each table
        production_search_columns = ["product", "design", "sku", "po_no"]
        cutting_search_columns = ["product", "design", "sku", "po_no"]
        sales_order_search_columns = ["po_no", "customer_name"]
        pending_order_search_columns = ["shipment_id", "product", "channel_abb"]

        # Fetch results from different tables
        production_results = get_all_data("tab_production", search_term=query, columns=production_search_columns)
        cutting_results = get_all_data("tab_cutting", search_term=query, columns=cutting_search_columns)
        sales_order_results = get_all_data("tab_sales_order", search_term=query, columns=sales_order_search_columns)
        pending_order_results = get_all_data("tab_inprod", search_term=query, columns=pending_order_search_columns)

    return render_template('search_results.html',
                           search_query=query,
                           production_results=production_results,
                           cutting_results=cutting_results,
                           sales_order_results=sales_order_results,
                           pending_order_results=pending_order_results)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.dashboard'))

@bp.route('/reports/production/monthly')
@login_required
def monthly_production_report():
    # Fetch real data for demonstration
    months, production_data = get_monthly_production_data()
    
    return render_template('reports/monthly_production.html', months=months, production_data=production_data)

@bp.route('/reports/production/summary')
@login_required
def production_summary_report():
    summary_metrics = get_production_summary_metrics()
    return render_template('reports/production_summary_report.html', summary_metrics=summary_metrics)

@bp.route('/reports/cutting/monthly')
@login_required
def monthly_cutting_report():
    months, produced_quantities = get_monthly_cutting_data()
    return render_template('reports/monthly_cutting.html', months=months, production_data=produced_quantities)

@bp.route('/reports/cutting/summary')
@login_required
def cutting_summary_report():
    summary_metrics = get_cutting_summary_metrics()
    return render_template('reports/cutting_summary_report.html', summary_metrics=summary_metrics)

@bp.route('/reports/production/article_summary')
@login_required
def article_summary_report():
    selected_month = request.args.get('month')
    
    # Get available months for the dropdown
    available_months = get_available_production_months()
    print(f"Available months being sent to template: {available_months}")

    # Set a default month if none is selected and months are available
    if not selected_month and available_months:
        selected_month = available_months[0] # Default to the most recent month

    labels, quantities, rejection_data, production_percentage_data, total_produced_qty = [], [], [], [], 0
    if selected_month:
        labels, quantities, rejection_data, production_percentage_data, total_produced_qty = get_article_summary_data(selected_month)
    
    return render_template('reports/article_summary.html',
                           labels=labels,
                           quantities=quantities,
                           rejection_data=rejection_data,
                           production_percentage_data=production_percentage_data,
                           total_produced_qty=total_produced_qty,
                           available_months=available_months,
                           selected_month=selected_month)

@bp.route('/reports/cutting/article_summary')
@login_required
def article_cutting_summary_report():
    selected_month = request.args.get('month')
    available_months = get_available_cutting_months()
    print(f"Available cutting months being sent to template: {available_months}")

    if not selected_month and available_months:
        selected_month = available_months[0]

    labels, quantities, rejection_data, production_percentage_data, total_produced_qty, total_rejection_qty = [], [], [], [], 0, 0
    if selected_month:
        labels, quantities, rejection_data, production_percentage_data, total_produced_qty, total_rejection_qty = get_article_cutting_summary_data(selected_month)

    return render_template('reports/article_summary_cutting.html',
                           labels=labels,
                           quantities=quantities,
                           rejection_data=rejection_data,
                           production_percentage_data=production_percentage_data,
                           total_produced_qty=total_produced_qty,
                           total_rejection_qty=total_rejection_qty,
                           available_months=available_months,
                           selected_month=selected_month) 