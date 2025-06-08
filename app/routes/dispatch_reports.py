from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import calendar
from app.utils.supabase_client import get_supabase_client
from collections import defaultdict

bp = Blueprint('dispatch', __name__, url_prefix='/reports')

def get_monthly_data(year, branch="all", channel="all", repository="all"):
    """Get monthly shipment data for the specified year."""
    supabase = get_supabase_client()
    
    query = supabase.table('tab_shipment_meta') \
        .select('month, branch, total_qty') \
        .gte('month', f'{year}-01-01') \
        .lt('month', f'{year + 1}-01-01') \
        .not_.ilike('shipment_id', '%Return%') \
        .not_.ilike('shipment_id', '%LPN%') \
        .not_.ilike('shipment_id', '%Mango%') \
        .not_.ilike('shipment_id', '%FMC%')

    if branch != "all":
        query = query.eq('branch', branch.capitalize())
    if channel != "all":
        query = query.eq('channel_abb', channel)
    if repository != "all":
        query = query.eq('repository', repository)

    response = query.execute()
    
    # Process the data
    monthly_data = defaultdict(lambda: {'karur': 0, 'mumbai': 0, 'total': 0})
    
    for record in response.data:
        month = datetime.strptime(record['month'], '%Y-%m-%d').strftime('%B')
        branch_name = record['branch'].lower()
        qty = record['total_qty'] or 0
        
        monthly_data[month]['total'] += qty
        if branch_name == 'karur':
            monthly_data[month]['karur'] += qty
        elif branch_name == 'mumbai':
            monthly_data[month]['mumbai'] += qty
    
    # Convert to list and sort by month
    months_order = list(calendar.month_name)[1:]
    result = []
    for month in months_order:
        if month in monthly_data:
            result.append({
                'month': month,
                **monthly_data[month]
            })
    
    return result

def get_quarterly_data(monthly_data):
    """Calculate quarterly data from monthly data."""
    quarters = {
        'Q1': {'months': ['January', 'February', 'March'], 'data': {'karur': 0, 'mumbai': 0, 'total': 0}},
        'Q2': {'months': ['April', 'May', 'June'], 'data': {'karur': 0, 'mumbai': 0, 'total': 0}},
        'Q3': {'months': ['July', 'August', 'September'], 'data': {'karur': 0, 'mumbai': 0, 'total': 0}},
        'Q4': {'months': ['October', 'November', 'December'], 'data': {'karur': 0, 'mumbai': 0, 'total': 0}}
    }
    
    for month_data in monthly_data:
        month = month_data['month']
        for quarter, info in quarters.items():
            if month in info['months']:
                info['data']['karur'] += month_data['karur']
                info['data']['mumbai'] += month_data['mumbai']
                info['data']['total'] += month_data['total']
    
    return [{'quarter': q, **d['data']} for q, d in quarters.items()]

def get_channel_data(year, branch="all", repository="all"):
    """Get channel-wise shipment data."""
    supabase = get_supabase_client()
    
    query = supabase.table('tab_shipment_meta') \
        .select('channel_abb, branch, total_qty') \
        .gte('month', f'{year}-01-01') \
        .lt('month', f'{year + 1}-01-01') \
        .not_.ilike('shipment_id', '%Return%') \
        .not_.ilike('shipment_id', '%LPN%') \
        .not_.ilike('shipment_id', '%Mango%') \
        .not_.ilike('shipment_id', '%FMC%')

    if branch != "all":
        query = query.eq('branch', branch.capitalize())
    if repository != "all":
        query = query.eq('repository', repository)

    response = query.execute()
    
    channel_data = defaultdict(lambda: {'count': 0, 'percentage': 0})
    total_count = 0
    
    for record in response.data:
        channel = record['channel_abb'] or 'Unknown'
        qty = record['total_qty'] or 0
        channel_data[channel]['count'] += qty
        total_count += qty
    
    # Calculate percentages
    for channel in channel_data:
        channel_data[channel]['percentage'] = round((channel_data[channel]['count'] / total_count * 100), 2) if total_count > 0 else 0
    
    return [{'channel': k, **v} for k, v in channel_data.items()]

def get_repository_data(year, branch="all", channel="all"):
    """Get repository-wise shipment data."""
    supabase = get_supabase_client()
    
    query = supabase.table('tab_shipment_meta') \
        .select('repository, branch, total_qty') \
        .gte('month', f'{year}-01-01') \
        .lt('month', f'{year + 1}-01-01') \
        .not_.ilike('shipment_id', '%Return%') \
        .not_.ilike('shipment_id', '%LPN%') \
        .not_.ilike('shipment_id', '%Mango%') \
        .not_.ilike('shipment_id', '%FMC%')

    if branch != "all":
        query = query.eq('branch', branch.capitalize())
    if channel != "all":
        query = query.eq('channel_abb', channel)

    response = query.execute()
    
    repo_data = defaultdict(lambda: {'count': 0, 'percentage': 0})
    total_count = 0
    
    for record in response.data:
        repo = record['repository'] or 'Unknown'
        qty = record['total_qty'] or 0
        repo_data[repo]['count'] += qty
        total_count += qty
    
    # Calculate percentages
    for repo in repo_data:
        repo_data[repo]['percentage'] = round((repo_data[repo]['count'] / total_count * 100), 2) if total_count > 0 else 0
    
    return [{'repository': k, **v} for k, v in repo_data.items()]

def get_branch_data(year, channel="all", repository="all"):
    """Get branch-wise shipment data."""
    supabase = get_supabase_client()
    
    query = supabase.table('tab_shipment_meta') \
        .select('branch, total_qty') \
        .gte('month', f'{year}-01-01') \
        .lt('month', f'{year + 1}-01-01') \
        .not_.ilike('shipment_id', '%Return%') \
        .not_.ilike('shipment_id', '%LPN%') \
        .not_.ilike('shipment_id', '%Mango%') \
        .not_.ilike('shipment_id', '%FMC%')

    if channel != "all":
        query = query.eq('channel_abb', channel)
    if repository != "all":
        query = query.eq('repository', repository)

    response = query.execute()
    
    branch_data = defaultdict(lambda: {'count': 0, 'percentage': 0})
    total_count = 0
    
    for record in response.data:
        branch = record['branch'] or 'Unknown'
        qty = record['total_qty'] or 0
        branch_data[branch]['count'] += qty
        total_count += qty
    
    # Calculate percentages
    for branch in branch_data:
        branch_data[branch]['percentage'] = round((branch_data[branch]['count'] / total_count * 100), 2) if total_count > 0 else 0
    
    return [{'branch': k, **v} for k, v in branch_data.items()]

def calculate_percentages(totals):
    """Calculate percentage distribution between branches."""
    total = totals['karur'] + totals['mumbai']
    if total == 0:
        return {'karur': 0, 'mumbai': 0}
    
    return {
        'karur': round((totals['karur'] / total) * 100, 2),
        'mumbai': round((totals['mumbai'] / total) * 100, 2)
    }

@bp.route('/dispatch/monthly')
def monthly_dispatch_report():
    """Route for monthly dispatch report."""
    # Get year from query parameters, default to current year
    year = int(request.args.get('year', datetime.now().year))
    branch = request.args.get('branch', 'all')
    channel = request.args.get('channel', 'all')
    repository = request.args.get('repository', 'all')
    
    # Get all required data
    monthly_data = get_monthly_data(year, branch, channel, repository)
    quarterly_data = get_quarterly_data(monthly_data)
    channel_data = get_channel_data(year, branch, repository)
    repository_data = get_repository_data(year, branch, channel)
    branch_data = get_branch_data(year, branch, repository)
    
    # Prepare data for charts
    monthly_labels = [m['month'] for m in monthly_data]
    monthly_karur = [m['karur'] for m in monthly_data]
    monthly_mumbai = [m['mumbai'] for m in monthly_data]
    
    quarterly_labels = [q['quarter'] for q in quarterly_data]
    quarterly_karur = [q['karur'] for q in quarterly_data]
    quarterly_mumbai = [q['mumbai'] for q in quarterly_data]
    
    channel_labels = [c['channel'] for c in channel_data]
    channel_data_values = [c['count'] for c in channel_data]
    
    repository_labels = [r['repository'] for r in repository_data]
    repository_data_values = [r['count'] for r in repository_data]
    
    branch_labels = [b['branch'] for b in branch_data]
    branch_data_values = [b['count'] for b in branch_data]
    
    # Get available years for the dropdown
    supabase = get_supabase_client()
    years_response = supabase.table('tab_shipment_meta') \
        .select('month') \
        .execute()
    
    years = sorted(list(set(
        datetime.strptime(record['month'], '%Y-%m-%d').year
        for record in years_response.data
    )))
    
    return render_template('dispatch_reports.html',
                         year=year,
                         years=years,
                         monthly_data=monthly_data,
                         quarterly_data=quarterly_data,
                         channel_data=channel_data,
                         repository_data=repository_data,
                         branch_data=branch_data,
                         monthly_labels=monthly_labels,
                         monthly_karur=monthly_karur,
                         monthly_mumbai=monthly_mumbai,
                         quarterly_labels=quarterly_labels,
                         quarterly_karur=quarterly_karur,
                         quarterly_mumbai=quarterly_mumbai,
                         channel_labels=channel_labels,
                         channel_data_values=channel_data_values,
                         repository_labels=repository_labels,
                         repository_data_values=repository_data_values,
                         branch_labels=branch_labels,
                         branch_data_values=branch_data_values)

@bp.route('/dispatch/summary')
def dispatch_summary_report():
    """Route for dispatch summary report."""
    # Get year from query parameters, default to current year
    year = int(request.args.get('year', datetime.now().year))
    
    # Get monthly data
    monthly_data = get_monthly_data(year)
    
    # Calculate totals and averages
    totals = {
        'karur': sum(m['karur'] for m in monthly_data),
        'mumbai': sum(m['mumbai'] for m in monthly_data),
        'total': sum(m['total'] for m in monthly_data)
    }
    
    averages = {
        'karur': round(totals['karur'] / 12, 2),
        'mumbai': round(totals['mumbai'] / 12, 2),
        'total': round(totals['total'] / 12, 2)
    }
    
    # Calculate percentages
    percentages = calculate_percentages(totals)
    
    # Get available years for the dropdown
    supabase = get_supabase_client()
    years_response = supabase.table('tab_shipment_meta') \
        .select('month') \
        .execute()
    
    years = sorted(list(set(
        datetime.strptime(record['month'], '%Y-%m-%d').year
        for record in years_response.data
    )))
    
    return render_template('dispatch_summary.html',
                         year=year,
                         years=years,
                         totals=totals,
                         averages=averages,
                         percentages=percentages)

@bp.route('/api/dispatch/monthly')
def api_monthly_dispatch():
    """API endpoint for monthly dispatch data."""
    year = int(request.args.get('year', datetime.now().year))
    branch = request.args.get('branch', 'all')
    channel = request.args.get('channel', 'all')
    repository = request.args.get('repository', 'all')
    
    # Get all required data
    monthly_data = get_monthly_data(year, branch, channel, repository)
    quarterly_data = get_quarterly_data(monthly_data)
    channel_data = get_channel_data(year, branch, repository)
    repository_data = get_repository_data(year, branch, channel)
    branch_data = get_branch_data(year, branch, repository)
    
    # Prepare data for charts
    monthly_labels = [m['month'] for m in monthly_data]
    monthly_karur = [m['karur'] for m in monthly_data]
    monthly_mumbai = [m['mumbai'] for m in monthly_data]
    
    quarterly_labels = [q['quarter'] for q in quarterly_data]
    quarterly_karur = [q['karur'] for q in quarterly_data]
    quarterly_mumbai = [q['mumbai'] for q in quarterly_data]
    
    channel_labels = [c['channel'] for c in channel_data]
    channel_data_values = [c['count'] for c in channel_data]
    
    repository_labels = [r['repository'] for r in repository_data]
    repository_data_values = [r['count'] for r in repository_data]
    
    branch_labels = [b['branch'] for b in branch_data]
    branch_data_values = [b['count'] for b in branch_data]
    
    return jsonify({
        'monthly_data': monthly_data,
        'quarterly_data': quarterly_data,
        'channel_data': channel_data,
        'repository_data': repository_data,
        'branch_data': branch_data,
        'monthly_labels': monthly_labels,
        'monthly_karur': monthly_karur,
        'monthly_mumbai': monthly_mumbai,
        'quarterly_labels': quarterly_labels,
        'quarterly_karur': quarterly_karur,
        'quarterly_mumbai': quarterly_mumbai,
        'channel_labels': channel_labels,
        'channel_data_values': channel_data_values,
        'repository_labels': repository_labels,
        'repository_data_values': repository_data_values,
        'branch_labels': branch_labels,
        'branch_data_values': branch_data_values
    })

@bp.route('/api/dispatch/monthly/compare')
def api_monthly_compare():
    """API endpoint for comparing monthly data between two years."""
    year1 = int(request.args.get('year1', datetime.now().year))
    year2 = int(request.args.get('year2', datetime.now().year - 1))
    
    # Get data for both years
    monthly_data1 = get_monthly_data(year1)
    monthly_data2 = get_monthly_data(year2)
    
    # Prepare comparison data
    months = [m['month'] for m in monthly_data1]
    year1_karur = [m['karur'] for m in monthly_data1]
    year1_mumbai = [m['mumbai'] for m in monthly_data1]
    year2_karur = [m['karur'] for m in monthly_data2]
    year2_mumbai = [m['mumbai'] for m in monthly_data2]
    
    return jsonify({
        'months': months,
        'year1': year1,
        'year2': year2,
        'year1_karur': year1_karur,
        'year1_mumbai': year1_mumbai,
        'year2_karur': year2_karur,
        'year2_mumbai': year2_mumbai
    }) 