from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
from app import User
from app.models.data_models import get_monthly_production_data, get_available_production_months, get_article_summary_data, get_monthly_cutting_data, get_available_cutting_months, get_article_cutting_summary_data

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
    return render_template('reports.html')

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

@bp.route('/reports/cutting/monthly')
@login_required
def monthly_cutting_report():
    months, produced_quantities = get_monthly_cutting_data()
    return render_template('reports/monthly_cutting.html', months=months, production_data=produced_quantities)

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

    if not selected_month and available_months:
        selected_month = available_months[0]

    labels, quantities, rejection_data, production_percentage_data, total_produced_qty = [], [], [], [], 0
    if selected_month:
        labels, quantities, rejection_data, production_percentage_data, total_produced_qty = get_article_cutting_summary_data(selected_month)

    return render_template('reports/article_summary_cutting.html',
                           labels=labels,
                           quantities=quantities,
                           rejection_data=rejection_data,
                           production_percentage_data=production_percentage_data,
                           total_produced_qty=total_produced_qty,
                           available_months=available_months,
                           selected_month=selected_month) 