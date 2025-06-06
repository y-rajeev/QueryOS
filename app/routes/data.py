from flask import Blueprint, render_template, request
from app.models.data_models import get_paginated_data

bp = Blueprint('data', __name__)

TABLES = {
    "production": "tab_inprod",
    "cutting": "tab_cutting",
    "tab_production": "tab_production"
}

@bp.route("/production")
def production_data():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 10))
    
    data = get_paginated_data(TABLES["production"], search, page, limit)
    return render_template("production_data.html", **data)

@bp.route("/cutting")
def cutting():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 10))
    
    data = get_paginated_data(TABLES["cutting"], search, page, limit)
    return render_template("cutting.html", **data)

@bp.route("/tab-production")
def tab_production():
    search = request.args.get("search", "").strip()
    try:
        page = max(1, min(int(request.args.get("page", 1)), 9999))
    except ValueError:
        page = 1
    limit = int(request.args.get("limit", 10))
    
    data = get_paginated_data(TABLES["tab_production"], search, page, limit)
    return render_template("tab_production.html", **data) 