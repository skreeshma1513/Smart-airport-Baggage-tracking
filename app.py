import os
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify

from utils.priority_engine import calculate_priority, estimate_waiting_time, calculate_delay_risk

app = Flask(__name__)
app.secret_key = 'smart-baggage-system-2024'

# Path to database file
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')


# ==============================================================================
# Database Connection Management
# ==============================================================================

def get_db():
    """
    Get or create a thread-local SQLite database connection.
    Configures Row factory for dictionary-like access and enables foreign keys.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """
    Closes the database connection at the end of each request context.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_next_id(prefix, table, column):
    """
    Generate the next formatted sequential ID for a table (e.g., PAX1016, BG1016, AR1007).
    """
    db = get_db()
    rows = db.execute(f"SELECT {column} FROM {table} WHERE {column} LIKE ?", (f"{prefix}%",)).fetchall()
    max_num = 1000
    for r in rows:
        val = r[column]
        num_str = val[len(prefix):]
        if num_str.isdigit():
            num = int(num_str)
            if num > max_num:
                max_num = num
    return f"{prefix}{max_num + 1}"


def recalculate_all_baggage_metrics(db=None):
    """
    Recalculates priority score, queue rank, wait time, and delay risk
    for all active baggage items using the priority engine.
    """
    should_close = False
    if db is None:
        db = get_db()

    # 1. Update priority score, level, and reason for all baggage items
    baggage_items = db.execute('''
        SELECT b.id, b.baggage_id, b.status, p.category, p.assistance_required, p.age
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
    ''').fetchall()

    for item in baggage_items:
        pri = calculate_priority(item['category'], item['assistance_required'], item['age'])
        db.execute('''
            UPDATE baggage
            SET priority_score = ?, priority_level = ?, priority_reason = ?
            WHERE id = ?
        ''', (pri['score'], pri['level'], pri['reason'], item['id']))
    db.commit()

    # 2. Recalculate queue positions, wait times, and delay risks
    queue_items = db.execute('''
        SELECT id, priority_level, status
        FROM baggage
        WHERE status != 'Collected'
        ORDER BY priority_score DESC, id ASC
    ''').fetchall()

    total_in_queue = len(queue_items)
    for q_pos, q_item in enumerate(queue_items, start=1):
        wait = estimate_waiting_time(q_pos, q_item['priority_level'], q_item['status'])
        risk_info = calculate_delay_risk(q_pos, q_item['status'], total_in_queue, flight_delayed=(q_item['status'] == 'Delayed'))
        db.execute('''
            UPDATE baggage
            SET estimated_wait = ?, delay_risk = ?, delay_reason = ?
            WHERE id = ?
        ''', (wait, risk_info['risk'], risk_info['reason'], q_item['id']))

    # Collected items have zero wait time and low risk
    db.execute('''
        UPDATE baggage 
        SET estimated_wait = 0, delay_risk = 'LOW', delay_reason = 'Baggage already collected by passenger.'
        WHERE status = 'Collected'
    ''')
    db.commit()


# ==============================================================================
# Database Initialization & Sample Data
# ==============================================================================

def init_db():
    """
    Initializes tables and seeds sample data on first run.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passengers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            flight_number TEXT,
            category TEXT DEFAULT 'Normal',
            assistance_required TEXT DEFAULT 'None',
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS baggage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baggage_id TEXT UNIQUE NOT NULL,
            passenger_id TEXT NOT NULL,
            flight_number TEXT,
            status TEXT DEFAULT 'Checked In',
            priority_level TEXT DEFAULT 'LOW',
            priority_score INTEGER DEFAULT 0,
            priority_reason TEXT,
            checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estimated_wait INTEGER DEFAULT 0,
            delay_risk TEXT DEFAULT 'LOW',
            delay_reason TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assistance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT UNIQUE NOT NULL,
            passenger_id TEXT NOT NULL,
            assistance_type TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id TEXT,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # Check if sample data already exists
    cursor.execute('SELECT COUNT(*) FROM passengers')
    passenger_count = cursor.fetchone()[0]

    if passenger_count == 0:
        # 15 sample passengers
        sample_passengers = [
            ('PAX1001', 'Rajesh Kumar', 65, 'AI-202', 'Normal', 'None', '9876543001'),
            ('PAX1002', 'Anitha Sharma', 32, 'AI-202', 'Pregnant', 'None', '9876543002'),
            ('PAX1003', 'Mohammed Farooq', 78, '6E-305', 'Elderly', 'Wheelchair Assistance', '9876543003'),
            ('PAX1004', 'Priya Nair', 28, 'SG-401', 'Normal', 'None', '9876543004'),
            ('PAX1005', 'Suresh Babu', 72, 'AI-202', 'Elderly', 'Elderly Assistance', '9876543005'),
            ('PAX1006', 'Lakshmi Devi', 45, '6E-305', 'Differently-Abled', 'Wheelchair Assistance', '9876543006'),
            ('PAX1007', 'Vikram Singh', 35, 'SG-401', 'Normal', 'None', '9876543007'),
            ('PAX1008', 'Meena Kumari', 82, 'AI-505', 'Elderly', 'Elderly Assistance', '9876543008'),
            ('PAX1009', 'Arjun Reddy', 30, 'AI-505', 'Normal', 'None', '9876543009'),
            ('PAX1010', 'Fatima Begum', 29, '6E-305', 'Pregnant', 'General Assistance', '9876543010'),
            ('PAX1011', 'Karthik Rajan', 40, 'SG-401', 'Special Assistance', 'Baggage Collection Assistance', '9876543011'),
            ('PAX1012', 'Deepa Menon', 55, 'AI-202', 'Normal', 'None', '9876543012'),
            ('PAX1013', 'Ravi Shankar', 70, 'AI-505', 'Elderly', 'None', '9876543013'),
            ('PAX1014', 'Sana Khan', 26, '6E-305', 'Normal', 'None', '9876543014'),
            ('PAX1015', 'Gopal Krishna', 48, 'SG-401', 'Differently-Abled', 'Wheelchair Assistance', '9876543015')
        ]

        cursor.executemany('''
            INSERT INTO passengers (passenger_id, name, age, flight_number, category, assistance_required, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_passengers)
        conn.commit()

        # Varied statuses across baggage items
        sample_baggage_statuses = [
            'Claim Ready',  # BG1001 (PAX1001)
            'Processing',   # BG1002 (PAX1002)
            'Arrived',      # BG1003 (PAX1003)
            'Checked In',   # BG1004 (PAX1004)
            'Claim Ready',  # BG1005 (PAX1005)
            'Processing',   # BG1006 (PAX1006)
            'Loaded',       # BG1007 (PAX1007)
            'Arrived',      # BG1008 (PAX1008)
            'Delayed',      # BG1009 (PAX1009)
            'Processing',   # BG1010 (PAX1010)
            'Checked In',   # BG1011 (PAX1011)
            'Delayed',      # BG1012 (PAX1012)
            'Loaded',       # BG1013 (PAX1013)
            'Checked In',   # BG1014 (PAX1014)
            'Claim Ready'   # BG1015 (PAX1015)
        ]

        # Insert 15 baggage items with initial priority score calculation
        for idx, p in enumerate(sample_passengers, start=1):
            pax_id = p[0]
            age = p[2]
            flight = p[3]
            cat = p[4]
            asst = p[5]
            bg_id = f"BG{1000 + idx}"
            status = sample_baggage_statuses[idx - 1]

            pri = calculate_priority(cat, asst, age)
            cursor.execute('''
                INSERT INTO baggage (baggage_id, passenger_id, flight_number, status, priority_level, priority_score, priority_reason, estimated_wait, delay_risk, delay_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'LOW', '')
            ''', (bg_id, pax_id, flight, status, pri['level'], pri['score'], pri['reason']))

        conn.commit()

        # Calculate queue position, waiting time, and delay risk for all baggage
        queue_items = cursor.execute('''
            SELECT id, priority_level, status
            FROM baggage
            WHERE status != 'Collected'
            ORDER BY priority_score DESC, id ASC
        ''').fetchall()

        total_q = len(queue_items)
        for q_pos, q_item in enumerate(queue_items, start=1):
            wait = estimate_waiting_time(q_pos, q_item['priority_level'], q_item['status'])
            risk_info = calculate_delay_risk(q_pos, q_item['status'], total_q, flight_delayed=(q_item['status'] == 'Delayed'))
            cursor.execute('''
                UPDATE baggage
                SET estimated_wait = ?, delay_risk = ?, delay_reason = ?
                WHERE id = ?
            ''', (wait, risk_info['risk'], risk_info['reason'], q_item['id']))

        conn.commit()

        # 6 sample assistance requests
        sample_assistance = [
            ('AR1001', 'PAX1003', 'Wheelchair Assistance', 'Pending', 'Wheelchair requested at deboarding gate.'),
            ('AR1002', 'PAX1006', 'Wheelchair Assistance', 'Assigned', 'Transit staff allocated with wheelchair at gate.'),
            ('AR1003', 'PAX1005', 'Elderly Assistance', 'Completed', 'Assistance provided through security and boarding.'),
            ('AR1004', 'PAX1008', 'Elderly Assistance', 'Pending', 'Elderly passenger requires luggage and transfer guidance.'),
            ('AR1005', 'PAX1011', 'Baggage Collection Assistance', 'Pending', 'Assistance needed retrieving luggage from carousel.'),
            ('AR1006', 'PAX1010', 'General Assistance', 'Assigned', 'Staff assigned to assist with terminal directions.')
        ]

        cursor.executemany('''
            INSERT INTO assistance_requests (request_id, passenger_id, assistance_type, status, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_assistance)
        conn.commit()

        # 10 sample notifications
        sample_notifications = [
            ('PAX1003', 'Baggage BG1003 is being processed with priority.', 'info', 0),
            ('PAX1006', 'Wheelchair assistance assigned for PAX1006.', 'success', 0),
            ('PAX1009', 'Baggage BG1009 has been delayed due to ramp congestion.', 'danger', 0),
            ('PAX1001', 'Your priority baggage BG1001 is ready for collection at Belt 2.', 'success', 1),
            ('PAX1005', 'Your priority baggage BG1005 is ready for collection at Belt 2.', 'success', 1),
            ('PAX1008', 'Elderly assistance request AR1004 is queued and awaiting agent.', 'warning', 0),
            ('PAX1010', 'General assistance staff assigned for your arrival.', 'info', 0),
            ('PAX1012', 'Baggage BG1012 has been delayed during sorting inspection.', 'danger', 0),
            ('PAX1015', 'Your priority baggage BG1015 is ready for collection at Belt 4.', 'success', 0),
            ('PAX1002', 'Baggage BG1002 status updated to Processing.', 'info', 1)
        ]

        cursor.executemany('''
            INSERT INTO notifications (passenger_id, message, type, is_read)
            VALUES (?, ?, ?, ?)
        ''', sample_notifications)
        conn.commit()

    conn.close()


# Ensure tables and sample data exist upon startup
init_db()


@app.before_request
def ensure_db():
    """
    Hook to verify database is initialized before any incoming request.
    """
    if not getattr(app, '_db_initialized', False):
        init_db()
        app._db_initialized = True


# ==============================================================================
# Page Routes
# ==============================================================================

@app.route('/')
def dashboard():
    """
    GET / → dashboard.html
    Dashboard with operational metrics, priority queue overview, recent baggage updates,
    and latest notifications.
    """
    db = get_db()

    # Calculate operational statistics
    total_passengers = db.execute('SELECT COUNT(*) FROM passengers').fetchone()[0]
    total_baggage = db.execute('SELECT COUNT(*) FROM baggage').fetchone()[0]
    priority_baggage = db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'HIGH'").fetchone()[0]
    normal_baggage = db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'LOW'").fetchone()[0]
    claim_ready = db.execute("SELECT COUNT(*) FROM baggage WHERE status = 'Claim Ready'").fetchone()[0]
    delayed = db.execute("SELECT COUNT(*) FROM baggage WHERE status = 'Delayed'").fetchone()[0]
    pending_assistance = db.execute("SELECT COUNT(*) FROM assistance_requests WHERE status = 'Pending'").fetchone()[0]

    stats = {
        'total_passengers': total_passengers,
        'total_baggage': total_baggage,
        'priority_baggage': priority_baggage,
        'normal_baggage': normal_baggage,
        'claim_ready': claim_ready,
        'delayed': delayed,
        'pending_assistance': pending_assistance
    }

    # Top 10 priority baggage items joined with passenger details
    priority_queue = db.execute('''
        SELECT b.*, p.name as passenger_name, p.category, p.assistance_required
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        WHERE b.status != 'Collected'
        ORDER BY b.priority_score DESC, b.id ASC
        LIMIT 10
    ''').fetchall()

    # Latest 5 baggage updates
    recent_updates = db.execute('''
        SELECT b.*, p.name as passenger_name
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        ORDER BY b.updated_at DESC
        LIMIT 5
    ''').fetchall()

    # Latest 5 notifications
    notifications = db.execute('''
        SELECT * FROM notifications
        ORDER BY created_at DESC
        LIMIT 5
    ''').fetchall()

    return render_template(
        'dashboard.html',
        stats=stats,
        priority_queue=priority_queue,
        recent_updates=recent_updates,
        notifications=notifications
    )


@app.route('/passengers')
def passengers():
    """
    GET /passengers → passengers.html
    List passengers with optional search (name or ID) and category filtering.
    """
    db = get_db()
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = 'SELECT * FROM passengers WHERE 1=1'
    params = []

    if search:
        query += ' AND (name LIKE ? OR passenger_id LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    if category:
        query += ' AND category = ?'
        params.append(category)

    query += ' ORDER BY id ASC'
    passenger_list = db.execute(query, params).fetchall()

    categories = ['Normal', 'Elderly', 'Pregnant', 'Differently-Abled', 'Special Assistance']

    return render_template(
        'passengers.html',
        passengers=passenger_list,
        categories=categories,
        search=search,
        selected_category=category
    )


@app.route('/passengers/add', methods=['POST'])
def add_passenger():
    """
    POST /passengers/add
    Register a new passenger with auto-generated PAX id and calculate priority for baggage.
    """
    db = get_db()
    name = request.form.get('name', '').strip()
    age = request.form.get('age')
    flight_number = request.form.get('flight_number', '').strip().upper()
    category = request.form.get('category', 'Normal').strip()
    assistance_required = request.form.get('assistance_required', 'None').strip()
    phone = request.form.get('phone', '').strip()

    if not name or not flight_number:
        flash('Passenger name and flight number are required.', 'danger')
        return redirect(url_for('passengers'))

    age_int = int(age) if age and age.isdigit() else None
    passenger_id = get_next_id('PAX', 'passengers', 'passenger_id')

    db.execute('''
        INSERT INTO passengers (passenger_id, name, age, flight_number, category, assistance_required, phone)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (passenger_id, name, age_int, flight_number, category, assistance_required, phone))

    # Create confirmation notification
    db.execute('''
        INSERT INTO notifications (passenger_id, message, type)
        VALUES (?, ?, ?)
    ''', (passenger_id, f'New passenger {name} registered successfully.', 'info'))

    db.commit()
    flash(f'New passenger {name} ({passenger_id}) registered successfully.', 'success')
    return redirect(url_for('passengers'))


@app.route('/passengers/edit/<int:id>', methods=['POST'])
def edit_passenger(id):
    """
    POST /passengers/edit/<int:id>
    Update passenger details and recalculate priority metrics for associated baggage.
    """
    db = get_db()
    passenger = db.execute('SELECT * FROM passengers WHERE id = ?', (id,)).fetchone()
    if not passenger:
        flash('Passenger not found.', 'danger')
        return redirect(url_for('passengers'))

    name = request.form.get('name', passenger['name']).strip()
    age = request.form.get('age')
    flight_number = request.form.get('flight_number', passenger['flight_number']).strip().upper()
    category = request.form.get('category', passenger['category']).strip()
    assistance_required = request.form.get('assistance_required', passenger['assistance_required']).strip()
    phone = request.form.get('phone', passenger['phone']).strip()

    age_int = int(age) if age and str(age).isdigit() else passenger['age']

    db.execute('''
        UPDATE passengers
        SET name = ?, age = ?, flight_number = ?, category = ?, assistance_required = ?, phone = ?
        WHERE id = ?
    ''', (name, age_int, flight_number, category, assistance_required, phone, id))
    db.commit()

    # Recalculate priority scores and wait times for associated baggage
    recalculate_all_baggage_metrics(db)

    flash(f'Passenger {name} ({passenger["passenger_id"]}) updated successfully.', 'success')
    return redirect(url_for('passengers'))


@app.route('/passengers/delete/<int:id>', methods=['POST'])
def delete_passenger(id):
    """
    POST /passengers/delete/<int:id>
    Delete passenger and associated baggage, assistance requests, and notifications.
    """
    db = get_db()
    passenger = db.execute('SELECT * FROM passengers WHERE id = ?', (id,)).fetchone()
    if not passenger:
        flash('Passenger not found.', 'danger')
        return redirect(url_for('passengers'))

    pax_id = passenger['passenger_id']
    name = passenger['name']

    db.execute('DELETE FROM baggage WHERE passenger_id = ?', (pax_id,))
    db.execute('DELETE FROM assistance_requests WHERE passenger_id = ?', (pax_id,))
    db.execute('DELETE FROM notifications WHERE passenger_id = ?', (pax_id,))
    db.execute('DELETE FROM passengers WHERE id = ?', (id,))
    db.commit()

    recalculate_all_baggage_metrics(db)

    flash(f'Passenger {name} ({pax_id}) and all associated records deleted.', 'success')
    return redirect(url_for('passengers'))


@app.route('/baggage')
def baggage():
    """
    GET /baggage → baggage.html
    List baggage with optional search (baggage ID or passenger name) and status filtering.
    """
    db = get_db()
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    query = '''
        SELECT b.*, p.name as passenger_name, p.category, p.phone
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        WHERE 1=1
    '''
    params = []

    if search:
        query += ' AND (b.baggage_id LIKE ? OR p.name LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    if status:
        query += ' AND b.status = ?'
        params.append(status)

    query += ' ORDER BY b.priority_score DESC, b.id ASC'
    baggage_list = db.execute(query, params).fetchall()

    passengers_list = db.execute('SELECT * FROM passengers ORDER BY name ASC').fetchall()
    statuses = ['Checked In', 'Processing', 'Loaded', 'Arrived', 'Claim Ready', 'Collected', 'Delayed']

    return render_template(
        'baggage.html',
        baggage_list=baggage_list,
        passengers=passengers_list,
        statuses=statuses,
        search=search,
        selected_status=status
    )


@app.route('/baggage/add', methods=['POST'])
def add_baggage():
    """
    POST /baggage/add
    Register new baggage with auto-generated BG id, priority calculation,
    and estimated wait and delay risk calculation.
    """
    db = get_db()
    passenger_id = request.form.get('passenger_id', '').strip()
    status = request.form.get('status', 'Checked In').strip()
    flight_number = request.form.get('flight_number', '').strip().upper()

    passenger = db.execute('SELECT * FROM passengers WHERE passenger_id = ?', (passenger_id,)).fetchone()
    if not passenger:
        flash('Selected passenger does not exist.', 'danger')
        return redirect(url_for('baggage'))

    if not flight_number:
        flight_number = passenger['flight_number']

    baggage_id = get_next_id('BG', 'baggage', 'baggage_id')
    pri = calculate_priority(passenger['category'], passenger['assistance_required'], passenger['age'])

    wait = estimate_waiting_time(1, pri['level'], status)
    risk = calculate_delay_risk(1, status, 1, flight_delayed=(status == 'Delayed'))

    db.execute('''
        INSERT INTO baggage (baggage_id, passenger_id, flight_number, status, priority_level, priority_score, priority_reason, estimated_wait, delay_risk, delay_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (baggage_id, passenger_id, flight_number, status, pri['level'], pri['score'], pri['reason'], wait, risk['risk'], risk['reason']))

    # Create notification
    db.execute('''
        INSERT INTO notifications (passenger_id, message, type)
        VALUES (?, ?, ?)
    ''', (passenger_id, f'New baggage {baggage_id} registered for passenger {passenger["name"]}.', 'info'))

    db.commit()

    # Recalculate metrics for accurate queue positions
    recalculate_all_baggage_metrics(db)

    flash(f'Baggage {baggage_id} successfully registered for {passenger["name"]}.', 'success')
    return redirect(url_for('baggage'))


@app.route('/baggage/update-status/<int:id>', methods=['POST'])
def update_baggage_status(id):
    """
    POST /baggage/update-status/<int:id>
    Update baggage status, recalculate metrics, and generate status notifications.
    """
    db = get_db()
    item = db.execute('SELECT * FROM baggage WHERE id = ?', (id,)).fetchone()
    if not item:
        flash('Baggage item not found.', 'danger')
        return redirect(url_for('baggage'))

    new_status = request.form.get('status', item['status']).strip()
    baggage_id = item['baggage_id']
    passenger_id = item['passenger_id']

    db.execute('''
        UPDATE baggage
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, id))
    db.commit()

    recalculate_all_baggage_metrics(db)

    # Determine notification content and type based on status
    if new_status == 'Claim Ready':
        notif_msg = f'Your priority baggage {baggage_id} is ready for collection.'
        notif_type = 'success'
    elif new_status == 'Delayed':
        notif_msg = f'Baggage {baggage_id} has been delayed.'
        notif_type = 'danger'
    else:
        notif_msg = f'Baggage {baggage_id} status updated to {new_status}.'
        notif_type = 'info'

    db.execute('''
        INSERT INTO notifications (passenger_id, message, type)
        VALUES (?, ?, ?)
    ''', (passenger_id, notif_msg, notif_type))
    db.commit()

    flash(f'Baggage {baggage_id} status updated to {new_status}.', 'success')
    return redirect(url_for('baggage'))


@app.route('/baggage/delete/<int:id>', methods=['POST'])
def delete_baggage(id):
    """
    POST /baggage/delete/<int:id>
    Delete baggage item and recalculate queue metrics.
    """
    db = get_db()
    item = db.execute('SELECT * FROM baggage WHERE id = ?', (id,)).fetchone()
    if not item:
        flash('Baggage item not found.', 'danger')
        return redirect(url_for('baggage'))

    baggage_id = item['baggage_id']
    db.execute('DELETE FROM baggage WHERE id = ?', (id,))
    db.commit()

    recalculate_all_baggage_metrics(db)

    flash(f'Baggage {baggage_id} removed successfully.', 'success')
    return redirect(url_for('baggage'))


@app.route('/priority-queue')
def priority_queue():
    """
    GET /priority-queue → priority.html
    Display live priority queue ordered by priority_score DESC, excluding Collected status.
    """
    db = get_db()
    queue = db.execute('''
        SELECT b.*, p.name as passenger_name, p.category, p.assistance_required, p.phone
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        WHERE b.status != 'Collected'
        ORDER BY b.priority_score DESC, b.id ASC
    ''').fetchall()

    return render_template('priority.html', queue=queue)


@app.route('/assistance')
def assistance():
    """
    GET /assistance → assistance.html
    Display assistance requests with optional status filtering.
    """
    db = get_db()
    status = request.args.get('status', '').strip()

    query = '''
        SELECT ar.*, p.name as passenger_name, p.phone, p.flight_number
        FROM assistance_requests ar
        JOIN passengers p ON ar.passenger_id = p.passenger_id
        WHERE 1=1
    '''
    params = []

    if status:
        query += ' AND ar.status = ?'
        params.append(status)

    query += ' ORDER BY ar.created_at DESC'
    requests_list = db.execute(query, params).fetchall()

    passengers_list = db.execute('SELECT * FROM passengers ORDER BY name ASC').fetchall()
    assistance_types = [
        'Wheelchair Assistance',
        'Elderly Assistance',
        'Baggage Collection Assistance',
        'General Assistance'
    ]

    return render_template(
        'assistance.html',
        requests=requests_list,
        passengers=passengers_list,
        assistance_types=assistance_types,
        selected_status=status
    )


@app.route('/assistance/add', methods=['POST'])
def add_assistance():
    """
    POST /assistance/add
    Create a new assistance request with auto-generated AR id.
    """
    db = get_db()
    passenger_id = request.form.get('passenger_id', '').strip()
    assistance_type = request.form.get('assistance_type', '').strip()
    notes = request.form.get('notes', '').strip()

    passenger = db.execute('SELECT * FROM passengers WHERE passenger_id = ?', (passenger_id,)).fetchone()
    if not passenger:
        flash('Selected passenger does not exist.', 'danger')
        return redirect(url_for('assistance'))

    request_id = get_next_id('AR', 'assistance_requests', 'request_id')

    db.execute('''
        INSERT INTO assistance_requests (request_id, passenger_id, assistance_type, status, notes)
        VALUES (?, ?, ?, 'Pending', ?)
    ''', (request_id, passenger_id, assistance_type, notes))

    # Create notification: 'Assistance request received for {passenger_name}.'
    db.execute('''
        INSERT INTO notifications (passenger_id, message, type)
        VALUES (?, ?, ?)
    ''', (passenger_id, f'Assistance request received for {passenger["name"]}.', 'info'))

    db.commit()
    flash(f'Assistance request {request_id} created for {passenger["name"]}.', 'success')
    return redirect(url_for('assistance'))


@app.route('/assistance/update/<int:id>', methods=['POST'])
def update_assistance(id):
    """
    POST /assistance/update/<int:id>
    Update assistance request status and create corresponding notification.
    """
    db = get_db()
    req_item = db.execute('SELECT * FROM assistance_requests WHERE id = ?', (id,)).fetchone()
    if not req_item:
        flash('Assistance request not found.', 'danger')
        return redirect(url_for('assistance'))

    new_status = request.form.get('status', req_item['status']).strip()
    notes = request.form.get('notes', req_item['notes'])

    db.execute('''
        UPDATE assistance_requests
        SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, notes, id))

    request_id = req_item['request_id']
    passenger_id = req_item['passenger_id']

    if new_status == 'Completed':
        notif_msg = f'Assistance request {request_id} ({req_item["assistance_type"]}) has been completed.'
        notif_type = 'success'
    elif new_status == 'Assigned':
        notif_msg = f'Staff has been assigned for assistance request {request_id}.'
        notif_type = 'info'
    else:
        notif_msg = f'Assistance request {request_id} status updated to {new_status}.'
        notif_type = 'info'

    db.execute('''
        INSERT INTO notifications (passenger_id, message, type)
        VALUES (?, ?, ?)
    ''', (passenger_id, notif_msg, notif_type))

    db.commit()
    flash(f'Assistance request {request_id} updated to {new_status}.', 'success')
    return redirect(url_for('assistance'))


@app.route('/notifications')
def notifications():
    """
    GET /notifications → notifications.html
    Display all system and passenger notifications ordered by created_at DESC.
    """
    db = get_db()
    notifs = db.execute('SELECT * FROM notifications ORDER BY created_at DESC').fetchall()
    return render_template('notifications.html', notifications=notifs)


@app.route('/notifications/mark-read/<int:id>', methods=['POST'])
def mark_notification_read(id):
    """
    POST /notifications/mark-read/<int:id>
    Mark notification as read.
    """
    db = get_db()
    db.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (id,))
    db.commit()
    flash('Notification marked as read.', 'success')
    return redirect(url_for('notifications'))


@app.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """
    POST /notifications/mark-all-read
    Convenience route to mark all notifications as read.
    """
    db = get_db()
    db.execute('UPDATE notifications SET is_read = 1')
    db.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))


@app.route('/passenger-tracking')
def passenger_tracking():
    """
    GET /passenger-tracking → passenger_tracking.html
    Interactive passenger baggage tracking portal (driven by JS client).
    """
    return render_template('passenger_tracking.html')


@app.route('/reports')
def reports():
    """
    GET /reports → reports.html
    System analytics overview and metrics cards.
    """
    db = get_db()
    stats = {
        'total_passengers': db.execute('SELECT COUNT(*) FROM passengers').fetchone()[0],
        'total_baggage': db.execute('SELECT COUNT(*) FROM baggage').fetchone()[0],
        'priority_baggage': db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'HIGH'").fetchone()[0],
        'medium_baggage': db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'MEDIUM'").fetchone()[0],
        'normal_baggage': db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'LOW'").fetchone()[0],
        'claim_ready': db.execute("SELECT COUNT(*) FROM baggage WHERE status = 'Claim Ready'").fetchone()[0],
        'delayed': db.execute("SELECT COUNT(*) FROM baggage WHERE status = 'Delayed'").fetchone()[0],
        'in_processing': db.execute("SELECT COUNT(*) FROM baggage WHERE status = 'Processing'").fetchone()[0],
        'total_assistance': db.execute('SELECT COUNT(*) FROM assistance_requests').fetchone()[0],
        'pending_assistance': db.execute("SELECT COUNT(*) FROM assistance_requests WHERE status = 'Pending'").fetchone()[0],
        'completed_assistance': db.execute("SELECT COUNT(*) FROM assistance_requests WHERE status = 'Completed'").fetchone()[0]
    }
    return render_template('reports.html', stats=stats)


# ==============================================================================
# REST API Endpoints (Hardware & Frontend Integration)
# ==============================================================================

@app.route('/api/baggage/scan', methods=['POST'])
def api_baggage_scan():
    """
    POST /api/baggage/scan
    Scans a baggage item by barcode/RFID (e.g., from ESP32).
    Request body: {"baggage_id": "BG1001"}
    Returns baggage details with priority info as JSON or 404 if not found.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    baggage_id = data.get('baggage_id', '').strip() if data else ''

    if not baggage_id:
        return jsonify({'error': 'baggage_id is required in request body'}), 400

    db = get_db()
    item = db.execute('''
        SELECT b.*, p.name as passenger_name, p.category, p.assistance_required, p.phone, p.age
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        WHERE b.baggage_id = ?
    ''', (baggage_id,)).fetchone()

    if not item:
        return jsonify({'error': f'Baggage {baggage_id} not found'}), 404

    res_dict = dict(item)
    res_dict['passenger'] = res_dict.get('passenger_name')
    return jsonify(res_dict)


@app.route('/api/baggage/<baggage_id>', methods=['GET'])
def api_get_baggage(baggage_id):
    """
    GET /api/baggage/<baggage_id>
    Return baggage details with passenger info as JSON.
    """
    db = get_db()
    item = db.execute('''
        SELECT b.*, p.name as passenger_name, p.category, p.assistance_required, p.phone, p.age
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        WHERE b.baggage_id = ?
    ''', (baggage_id,)).fetchone()

    if not item:
        return jsonify({'error': f'Baggage {baggage_id} not found'}), 404

    return jsonify(dict(item))


@app.route('/api/priority-queue', methods=['GET'])
def api_priority_queue():
    """
    GET /api/priority-queue
    Return full priority queue as JSON array (excluding status='Collected').
    """
    db = get_db()
    items = db.execute('''
        SELECT b.*, p.name as passenger_name, p.category, p.assistance_required, p.phone
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        WHERE b.status != 'Collected'
        ORDER BY b.priority_score DESC, b.id ASC
    ''').fetchall()

    return jsonify([dict(item) for item in items])


@app.route('/api/baggage/status', methods=['POST'])
def api_update_baggage_status():
    """
    POST /api/baggage/status
    Request body: {"baggage_id": "BG1001", "status": "Processing"}
    Update status, recalculate metrics, and return updated baggage as JSON.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    baggage_id = data.get('baggage_id', '').strip()
    new_status = data.get('status', '').strip()

    if not baggage_id or not new_status:
        return jsonify({'error': 'Both baggage_id and status are required'}), 400

    db = get_db()
    item = db.execute('SELECT * FROM baggage WHERE baggage_id = ?', (baggage_id,)).fetchone()
    if not item:
        return jsonify({'error': f'Baggage {baggage_id} not found'}), 404

    db.execute('''
        UPDATE baggage
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE baggage_id = ?
    ''', (new_status, baggage_id))
    db.commit()

    recalculate_all_baggage_metrics(db)

    # Notification dispatch
    if new_status == 'Claim Ready':
        notif_msg = f'Your priority baggage {baggage_id} is ready for collection.'
        notif_type = 'success'
    elif new_status == 'Delayed':
        notif_msg = f'Baggage {baggage_id} has been delayed.'
        notif_type = 'danger'
    else:
        notif_msg = f'Baggage {baggage_id} status updated to {new_status}.'
        notif_type = 'info'

    db.execute('''
        INSERT INTO notifications (passenger_id, message, type)
        VALUES (?, ?, ?)
    ''', (item['passenger_id'], notif_msg, notif_type))
    db.commit()

    updated = db.execute('''
        SELECT b.*, p.name as passenger_name, p.category, p.assistance_required, p.phone
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        WHERE b.baggage_id = ?
    ''', (baggage_id,)).fetchone()

    return jsonify(dict(updated))


@app.route('/api/track', methods=['GET'])
def api_track():
    """
    GET /api/track?query=PAX1001 or GET /api/track?query=BG1001
    Returns tracking info as JSON: passenger details, baggage details,
    priority info, delay risk, assistance requests, and status journey.
    """
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query parameter is required (passenger_id or baggage_id)'}), 400

    db = get_db()

    # 1. Check if query matches baggage_id
    baggage_row = db.execute('SELECT * FROM baggage WHERE baggage_id = ?', (query,)).fetchone()
    if baggage_row:
        passenger_row = db.execute('SELECT * FROM passengers WHERE passenger_id = ?', (baggage_row['passenger_id'],)).fetchone()
        baggage_list = [dict(baggage_row)]
    else:
        # 2. Check if query matches passenger_id
        passenger_row = db.execute('SELECT * FROM passengers WHERE passenger_id = ?', (query,)).fetchone()
        if passenger_row:
            baggage_rows = db.execute('SELECT * FROM baggage WHERE passenger_id = ?', (passenger_row['passenger_id'],)).fetchall()
            baggage_list = [dict(b) for b in baggage_rows]
        else:
            # 3. Friendly fallback: search by passenger name
            passenger_row = db.execute('SELECT * FROM passengers WHERE name LIKE ?', (f'%{query}%',)).fetchone()
            if passenger_row:
                baggage_rows = db.execute('SELECT * FROM baggage WHERE passenger_id = ?', (passenger_row['passenger_id'],)).fetchall()
                baggage_list = [dict(b) for b in baggage_rows]
            else:
                return jsonify({'error': f'No tracking information found for "{query}"'}), 404

    passenger_dict = dict(passenger_row)
    p_id = passenger_dict['passenger_id']

    # Retrieve passenger's assistance requests and notifications
    assistance_rows = db.execute('SELECT * FROM assistance_requests WHERE passenger_id = ? ORDER BY created_at DESC', (p_id,)).fetchall()
    notification_rows = db.execute('SELECT * FROM notifications WHERE passenger_id = ? ORDER BY created_at DESC', (p_id,)).fetchall()

    primary_baggage = baggage_list[0] if baggage_list else None
    current_status = primary_baggage['status'] if primary_baggage else 'Checked In'
    is_delayed = (current_status == 'Delayed')

    # Construct the chronological journey stages
    all_stages = ['Checked In', 'Processing', 'Loaded', 'Arrived', 'Claim Ready', 'Collected']
    current_step_index = -1
    if not is_delayed and current_status in all_stages:
        current_step_index = all_stages.index(current_status)

    journey_steps = []
    for idx, stage in enumerate(all_stages):
        if is_delayed:
            state = 'completed' if idx == 0 else ('delayed' if idx == 1 else 'upcoming')
        else:
            if idx < current_step_index:
                state = 'completed'
            elif idx == current_step_index:
                state = 'current'
            else:
                state = 'upcoming'

        journey_steps.append({
            'step': stage,
            'state': state,
            'is_active': (idx == current_step_index or (is_delayed and idx == 1))
        })

    return jsonify({
        'passenger': passenger_dict,
        'baggage': baggage_list,
        'primary_baggage': primary_baggage,
        'priority_info': {
            'level': primary_baggage['priority_level'] if primary_baggage else 'LOW',
            'score': primary_baggage['priority_score'] if primary_baggage else 0,
            'reason': primary_baggage['priority_reason'] if primary_baggage else 'Standard handling',
            'priority_level': primary_baggage['priority_level'] if primary_baggage else 'LOW',
            'priority_score': primary_baggage['priority_score'] if primary_baggage else 0,
            'priority_reason': primary_baggage['priority_reason'] if primary_baggage else 'Standard handling'
        },
        'delay_risk': {
            'risk': primary_baggage['delay_risk'] if primary_baggage else 'LOW',
            'reason': primary_baggage['delay_reason'] if primary_baggage else 'Normal queue levels.',
            'estimated_wait': primary_baggage['estimated_wait'] if primary_baggage else 0
        },
        'assistance_requests': [dict(a) for a in assistance_rows],
        'notifications': [dict(n) for n in notification_rows],
        'status_journey': {
            'current_status': current_status,
            'is_delayed': is_delayed,
            'steps': journey_steps
        }
    })


@app.route('/api/reports/data', methods=['GET'])
def api_reports_data():
    """
    GET /api/reports/data
    Return all chart data as JSON:
    - priority_distribution: {high, medium, low}
    - status_distribution: {status: count for each status}
    - category_distribution: {category: count for each category}
    - assistance_distribution: {type: count}
    - delayed_by_flight: {flight: count}
    """
    db = get_db()

    # Priority distribution (supports lowercase & uppercase keys for client compatibility)
    high_count = db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'HIGH'").fetchone()[0]
    med_count = db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'MEDIUM'").fetchone()[0]
    low_count = db.execute("SELECT COUNT(*) FROM baggage WHERE priority_level = 'LOW'").fetchone()[0]

    priority_distribution = {
        'high': high_count,
        'medium': med_count,
        'low': low_count,
        'HIGH': high_count,
        'MEDIUM': med_count,
        'LOW': low_count
    }

    # Status distribution
    statuses = ['Checked In', 'Processing', 'Loaded', 'Arrived', 'Claim Ready', 'Collected', 'Delayed']
    status_distribution = {}
    for s in statuses:
        cnt = db.execute("SELECT COUNT(*) FROM baggage WHERE status = ?", (s,)).fetchone()[0]
        status_distribution[s] = cnt

    # Category distribution
    categories = ['Normal', 'Elderly', 'Pregnant', 'Differently-Abled', 'Special Assistance']
    category_distribution = {}
    for c in categories:
        cnt = db.execute("SELECT COUNT(*) FROM passengers WHERE category = ?", (c,)).fetchone()[0]
        category_distribution[c] = cnt

    # Assistance type distribution
    assistance_types = [
        'Wheelchair Assistance',
        'Elderly Assistance',
        'Baggage Collection Assistance',
        'General Assistance'
    ]
    assistance_distribution = {}
    for a in assistance_types:
        cnt = db.execute("SELECT COUNT(*) FROM assistance_requests WHERE assistance_type = ?", (a,)).fetchone()[0]
        assistance_distribution[a] = cnt

    # Delayed baggage grouped by flight
    delayed_rows = db.execute('''
        SELECT flight_number, COUNT(*) as count
        FROM baggage
        WHERE status = 'Delayed'
        GROUP BY flight_number
    ''').fetchall()
    delayed_by_flight = {row['flight_number']: row['count'] for row in delayed_rows}

    return jsonify({
        'priority_distribution': priority_distribution,
        'status_distribution': status_distribution,
        'category_distribution': category_distribution,
        'assistance_distribution': assistance_distribution,
        'delayed_by_flight': delayed_by_flight
    })


@app.route('/api/passengers', methods=['GET'])
def api_passengers():
    """
    GET /api/passengers
    Return all passengers as JSON array.
    """
    db = get_db()
    passengers_list = db.execute('SELECT * FROM passengers ORDER BY id ASC').fetchall()
    return jsonify([dict(p) for p in passengers_list])


@app.route('/api/baggage', methods=['GET'])
def api_all_baggage():
    """
    GET /api/baggage
    Return all baggage joined with passenger details as JSON array.
    """
    db = get_db()
    items = db.execute('''
        SELECT b.*, p.name as passenger_name, p.category, p.assistance_required, p.phone
        FROM baggage b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        ORDER BY b.priority_score DESC, b.id ASC
    ''').fetchall()
    return jsonify([dict(item) for item in items])


# ==============================================================================
# Application Entry Point
# ==============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
