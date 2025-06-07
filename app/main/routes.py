from flask import render_template
from flask_login import login_required

@bp.route('/reports')
@login_required
def reports():
    return render_template('reports.html') 