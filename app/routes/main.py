from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, login_user, logout_user, current_user
from app import User
from app.models.data_models import get_monthly_production_data

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