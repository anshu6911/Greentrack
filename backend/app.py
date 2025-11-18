from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import html
from datetime import datetime
from functools import wraps

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'green-track-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), '..', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
CORS(app, supports_credentials=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

REWARD_TIERS = [
    {
        'tier': 1,
        'threshold': 3,
        'brand': 'Swiggy',
        'code': 'SWIGGY-50-OFF',
        'description': 'Flat 50 off on your next food order.'
    },
    {
        'tier': 2,
        'threshold': 5,
        'brand': 'Zomato',
        'code': 'ZOMATO-75-OFF',
        'description': 'Save up to 75 on food delivery.'
    },
    {
        'tier': 3,
        'threshold': 10,
        'brand': 'Blinkit',
        'code': 'BLINKIT-10PCT',
        'description': '10% off on your next grocery order.'
    },
    {
        'tier': 4,
        'threshold': 15,
        'brand': 'Ola',
        'code': 'OLA-RIDE-100',
        'description': 'Get up to 100 off on cab rides.'
    },
    {
        'tier': 5,
        'threshold': 20,
        'brand': 'Uber',
        'code': 'UBER-GREEN-75',
        'description': 'Ride savings for helping keep the city clean.'
    },
    {
        'tier': 6,
        'threshold': 30,
        'brand': 'KFC',
        'code': 'KFC-MEAL-75',
        'description': 'Discount on your next KFC meal.'
    },
    {
        'tier': 7,
        'threshold': 40,
        'brand': "Domino's",
        'code': 'DOMINOS-PIZZA-100',
        'description': 'Flat 100 off on pizza orders.'
    }
]


def sanitize_text(value):
    if value is None:
        return ''
    return html.escape(value.strip())


def to_float(value):
    try:
        return float(value) if value not in (None, '', 'null') else None
    except (TypeError, ValueError):
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    """Get database connection"""
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    """Initialize database with tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('citizen', 'volunteer', 'moderator', 'admin')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high')),
            location_text TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            photo_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'valid', 'invalid', 'assigned', 'in_progress', 'completed')),
            moderator_notes TEXT,
            is_anonymous INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (citizen_id) REFERENCES users(id)
        )
    ''')
    
    # Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            assigned_volunteer_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'assigned', 'in_progress', 'completed')),
            assigned_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES reports(id),
            FOREIGN KEY (assigned_volunteer_id) REFERENCES users(id)
        )
    ''')
    
    # Proofs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proofs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            volunteer_id INTEGER NOT NULL,
            proof_photo_path TEXT,
            notes TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (volunteer_id) REFERENCES users(id)
        )
    ''')

    # Rewards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tier INTEGER NOT NULL,
            brand TEXT NOT NULL,
            code TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()


def award_rewards_for_citizen(citizen_id, conn):
    """Award rewards to a citizen based on their non-invalid reports."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM reports
        WHERE citizen_id = ?
          AND status = 'completed'
    ''', (citizen_id,))
    row = cursor.fetchone()
    valid_count = row['count'] if row else 0

    cursor.execute('SELECT tier FROM rewards WHERE user_id = ?', (citizen_id,))
    awarded_tiers = {r['tier'] for r in cursor.fetchall()}

    for tier in REWARD_TIERS:
        if valid_count >= tier['threshold'] and tier['tier'] not in awarded_tiers:
            cursor.execute('''
                INSERT INTO rewards (user_id, tier, brand, code, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (citizen_id, tier['tier'], tier['brand'], tier['code'], tier['description']))

def require_login(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            if 'user_role' not in session or session['user_role'] not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'citizen')
    
    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
    
    if role not in ['citizen', 'volunteer', 'moderator', 'admin']:
        role = 'citizen'
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if email exists
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create user
    password_hash = generate_password_hash(password)
    cursor.execute('''
        INSERT INTO users (name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    ''', (name, email, password_hash, role))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Registration successful', 'user_id': user_id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, password_hash, role FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_role'] = user['role']
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        }
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/me', methods=['GET'])
@require_login
def get_current_user():
    return jsonify({
        'id': session['user_id'],
        'name': session['user_name'],
        'email': session['user_email'],
        'role': session['user_role']
    })


@app.route('/api/rewards', methods=['GET'])
@require_login
def get_rewards():
    conn = get_db()
    award_rewards_for_citizen(session['user_id'], conn)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM reports
        WHERE citizen_id = ?
          AND status = 'completed'
    ''', (session['user_id'],))
    row = cursor.fetchone()
    valid_count = row['count'] if row else 0

    cursor.execute('''
        SELECT tier, brand, code, description, created_at
        FROM rewards
        WHERE user_id = ?
        ORDER BY tier ASC
    ''', (session['user_id'],))
    rewards = []
    awarded_tiers = set()
    for r in cursor.fetchall():
        rewards.append({
            'tier': r['tier'],
            'brand': r['brand'],
            'code': r['code'],
            'description': r['description'],
            'created_at': r['created_at']
        })
        awarded_tiers.add(r['tier'])

    next_tier = None
    for tier in REWARD_TIERS:
        if tier['tier'] not in awarded_tiers:
            next_tier = {
                'tier': tier['tier'],
                'threshold': tier['threshold'],
                'brand': tier['brand']
            }
            break

    conn.commit()
    conn.close()

    return jsonify({
        'valid_reports': valid_count,
        'rewards': rewards,
        'next_tier': next_tier
    })

# Reports routes
@app.route('/api/reports', methods=['POST'])
@require_login
def create_report():
    if session.get('user_role') not in ('citizen', 'admin', 'moderator'):
        return jsonify({'error': 'Citizens only'}), 403

    if 'photo' not in request.files:
        return jsonify({'error': 'Photo is required'}), 400
    
    file = request.files['photo']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file. Only JPG or PNG allowed'}), 400
    
    category = sanitize_text(request.form.get('category', ''))
    description = sanitize_text(request.form.get('description', ''))
    severity = request.form.get('severity', 'medium')
    location_text = sanitize_text(request.form.get('location_text', ''))
    latitude = to_float(request.form.get('latitude'))
    longitude = to_float(request.form.get('longitude'))
    is_anonymous = 1 if request.form.get('is_anonymous', 'false').lower() == 'true' else 0
    
    if not category or not description or not location_text:
        return jsonify({'error': 'Category, description, and location are required'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Store relative path
    photo_path = f'uploads/{filename}'
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reports (citizen_id, category, description, severity, location_text, latitude, longitude, photo_path, status, is_anonymous)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    ''', (session['user_id'], category, description, severity, location_text, 
          latitude, longitude, photo_path, is_anonymous))
    
    report_id = cursor.lastrowid
    
    # Create task
    cursor.execute('''
        INSERT INTO tasks (report_id, status)
        VALUES (?, 'pending')
    ''', (report_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Report created successfully', 'report_id': report_id}), 201

@app.route('/api/reports/my', methods=['GET'])
@require_login
def get_my_reports():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, t.status as task_status, t.id as task_id
        FROM reports r
        LEFT JOIN tasks t ON r.id = t.report_id
        WHERE r.citizen_id = ?
        ORDER BY r.created_at DESC
    ''', (session['user_id'],))
    
    reports = []
    for row in cursor.fetchall():
        reports.append({
            'id': row['id'],
            'category': row['category'],
            'description': row['description'],
            'severity': row['severity'],
            'location_text': row['location_text'],
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'photo_path': row['photo_path'],
            'status': row['status'],
            'moderator_notes': row['moderator_notes'],
            'is_anonymous': row['is_anonymous'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'task_status': row['task_status'],
            'task_id': row['task_id']
        })
    
    conn.close()
    return jsonify(reports)

@app.route('/api/reports/pending', methods=['GET'])
@require_role('moderator', 'admin')
def get_pending_reports():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, u.name as citizen_name, u.email as citizen_email
        FROM reports r
        JOIN users u ON r.citizen_id = u.id
        WHERE r.status = 'pending'
        ORDER BY r.created_at DESC
    ''')
    
    reports = []
    for row in cursor.fetchall():
        reports.append(dict(row))
    
    conn.close()
    return jsonify(reports)

@app.route('/api/reports/<int:report_id>/validate', methods=['POST'])
@require_role('moderator', 'admin')
def validate_report(report_id):
    data = request.get_json()
    is_valid = data.get('is_valid', True)
    notes = data.get('notes', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT citizen_id FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        return jsonify({'error': 'Report not found'}), 404
    
    new_status = 'valid' if is_valid else 'invalid'
    cursor.execute('''
        UPDATE reports
        SET status = ?, moderator_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, notes, report_id))
    
    cursor.execute('''
        UPDATE tasks
        SET status = 'pending', assigned_volunteer_id = NULL
        WHERE report_id = ?
    ''', (report_id,))

    if is_valid:
        award_rewards_for_citizen(report['citizen_id'], conn)
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Report marked as {new_status}'})

@app.route('/api/reports/<int:report_id>/assign', methods=['POST'])
@require_role('moderator', 'admin')
def assign_report(report_id):
    data = request.get_json()
    volunteer_id = data.get('volunteer_id')
    
    if not volunteer_id:
        return jsonify({'error': 'Volunteer ID is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT status FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        return jsonify({'error': 'Report not found'}), 404
    if report['status'] == 'invalid':
        conn.close()
        return jsonify({'error': 'Cannot assign an invalid report'}), 400
    
    # Verify volunteer exists and is a volunteer
    cursor.execute('SELECT id, role FROM users WHERE id = ?', (volunteer_id,))
    volunteer = cursor.fetchone()
    if not volunteer or volunteer['role'] not in ['volunteer', 'admin']:
        return jsonify({'error': 'Invalid volunteer'}), 400
    
    # Update report status
    cursor.execute('''
        UPDATE reports
        SET status = 'assigned', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (report_id,))
    
    # Update task
    cursor.execute('''
        UPDATE tasks
        SET assigned_volunteer_id = ?, status = 'assigned', assigned_at = CURRENT_TIMESTAMP
        WHERE report_id = ?
    ''', (volunteer_id, report_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Task assigned successfully'})

# Tasks routes
@app.route('/api/tasks/available', methods=['GET'])
@require_role('volunteer', 'admin')
def get_available_tasks():
    conn = get_db()
    cursor = conn.cursor()
    search = sanitize_text(request.args.get('q', ''))
    query = '''
        SELECT r.*, t.id as task_id, t.status as task_status,
               u.name as citizen_name
        FROM reports r
        JOIN tasks t ON r.id = t.report_id
        JOIN users u ON r.citizen_id = u.id
        WHERE r.status IN ('pending', 'valid')
        AND t.status = 'pending'
        AND t.assigned_volunteer_id IS NULL
    '''
    params = []
    if search:
        query += ' AND (r.location_text LIKE ? OR r.description LIKE ?)'
        like = f'%{search}%'
        params.extend([like, like])
    query += ' ORDER BY r.created_at DESC'
    cursor.execute(query, params)
    
    tasks = []
    for row in cursor.fetchall():
        tasks.append(dict(row))
    
    conn.close()
    return jsonify(tasks)


@app.route('/api/tasks/my', methods=['GET'])
@require_role('volunteer', 'admin')
def get_my_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, t.id as task_id, t.status as task_status,
               t.assigned_at, t.completed_at,
               p.proof_photo_path, p.notes as proof_notes
        FROM reports r
        JOIN tasks t ON r.id = t.report_id
        LEFT JOIN proofs p ON p.task_id = t.id
        WHERE t.assigned_volunteer_id = ?
        ORDER BY COALESCE(t.assigned_at, r.created_at) DESC
    ''', (session['user_id'],))

    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(tasks)


@app.route('/api/tasks/manage', methods=['GET'])
@require_role('moderator', 'admin')
def manage_tasks():
    status = request.args.get('status', '').strip()
    category = sanitize_text(request.args.get('category', '').strip())
    search = sanitize_text(request.args.get('q', '').strip())

    valid_task_statuses = {'pending', 'assigned', 'in_progress', 'completed'}
    if status and status not in valid_task_statuses:
        status = ''

    conn = get_db()
    cursor = conn.cursor()
    query = '''
        SELECT t.id as task_id, t.status, t.assigned_at, t.completed_at,
               r.category, r.description, r.location_text, r.severity,
               r.status as report_status,
               v.name as volunteer_name
        FROM tasks t
        JOIN reports r ON t.report_id = r.id
        LEFT JOIN users v ON t.assigned_volunteer_id = v.id
        WHERE 1=1
    '''
    params = []
    if status:
        query += ' AND t.status = ?'
        params.append(status)
    if category:
        query += ' AND r.category = ?'
        params.append(category)
    if search:
        query += ' AND (r.description LIKE ? OR r.location_text LIKE ?)'
        like = f'%{search}%'
        params.extend([like, like])
    query += ' ORDER BY r.created_at DESC'

    cursor.execute(query, params)
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(tasks)

@app.route('/api/tasks/<int:task_id>/claim', methods=['POST'])
@require_role('volunteer', 'admin')
def claim_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if task exists and is available
    cursor.execute('''
        SELECT t.*, r.status as report_status
        FROM tasks t
        JOIN reports r ON t.report_id = r.id
        WHERE t.id = ?
    ''', (task_id,))
    
    task = cursor.fetchone()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    if task['status'] not in ('pending', 'assigned'):
        return jsonify({'error': 'Task cannot be claimed'}), 400
    
    if task['assigned_volunteer_id'] and task['assigned_volunteer_id'] != session['user_id']:
        return jsonify({'error': 'Task already assigned'}), 400
    
    # Assign to current user
    cursor.execute('''
        UPDATE tasks
        SET assigned_volunteer_id = ?, status = 'assigned', assigned_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (session['user_id'], task_id))
    
    cursor.execute('''
        UPDATE reports
        SET status = 'assigned', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (task['report_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Task claimed successfully'})

@app.route('/api/tasks/<int:task_id>/start', methods=['POST'])
@require_role('volunteer', 'admin')
def start_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT report_id, status FROM tasks WHERE id = ? AND assigned_volunteer_id = ?', 
                   (task_id, session['user_id']))
    task = cursor.fetchone()
    
    if not task:
        return jsonify({'error': 'Task not found or not assigned to you'}), 404
    if task['status'] == 'completed':
        return jsonify({'error': 'Task already completed'}), 400
    
    cursor.execute('''
        UPDATE tasks
        SET status = 'in_progress'
        WHERE id = ?
    ''', (task_id,))
    
    cursor.execute('''
        UPDATE reports
        SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (task['report_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Task started'})

@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
@require_role('volunteer', 'admin')
def complete_task(task_id):
    if 'proof_photo' not in request.files:
        return jsonify({'error': 'Proof photo is required'}), 400
    
    file = request.files['proof_photo']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file. Only JPG or PNG allowed'}), 400
    
    notes = request.form.get('notes', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT report_id, status FROM tasks WHERE id = ? AND assigned_volunteer_id = ?', 
                   (task_id, session['user_id']))
    task = cursor.fetchone()
    
    if not task:
        return jsonify({'error': 'Task not found or not assigned to you'}), 404
    if task['status'] not in ('assigned', 'in_progress'):
        return jsonify({'error': 'Task is not in a completable state'}), 400
    
    # Save proof photo
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    proof_photo_path = f'uploads/{filename}'
    
    # Create proof record
    cursor.execute('''
        INSERT INTO proofs (task_id, volunteer_id, proof_photo_path, notes)
        VALUES (?, ?, ?, ?)
    ''', (task_id, session['user_id'], proof_photo_path, notes))
    
    # Update task
    cursor.execute('''
        UPDATE tasks
        SET status = 'completed', completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (task_id,))
    
    # Update report
    cursor.execute('''
        UPDATE reports
        SET status = 'completed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (task['report_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Task completed successfully'})

# Analytics routes
@app.route('/api/stats', methods=['GET'])
@require_role('moderator', 'admin')
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    # Total reports
    cursor.execute('SELECT COUNT(*) as count FROM reports')
    total_reports = cursor.fetchone()['count']
    
    # Valid reports
    cursor.execute("SELECT COUNT(*) as count FROM reports WHERE status != 'invalid'")
    valid_reports = cursor.fetchone()['count']
    
    # Completed tasks
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'completed'")
    completed_tasks = cursor.fetchone()['count']
    
    # Volunteers count
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'volunteer'")
    volunteers_count = cursor.fetchone()['count']
    
    # Area hotspots (group by location_text)
    cursor.execute('''
        SELECT location_text, COUNT(*) as count
        FROM reports
        WHERE status != 'invalid'
        GROUP BY location_text
        ORDER BY count DESC
        LIMIT 10
    ''')
    hotspots = [{'location': row['location_text'], 'count': row['count']} 
                for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'total_reports': total_reports,
        'valid_reports': valid_reports,
        'completed_tasks': completed_tasks,
        'volunteers_count': volunteers_count,
        'hotspots': hotspots
    })


@app.route('/api/users/volunteers', methods=['GET'])
@require_role('moderator', 'admin')
def list_volunteers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, email
        FROM users
        WHERE role = 'volunteer'
        ORDER BY name
    ''')
    volunteers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(volunteers)

# Serve uploaded files
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Serve frontend files
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_frontend(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run app
    app.run(debug=True, host='0.0.0.0', port=5000)

