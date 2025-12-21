import os, logging
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, flash, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, Recording, User

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_SIZE_MB', 100)) * 1024 * 1024
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
logging.basicConfig(level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.ogg', '.flac'}

# Obscure upload subdomain (security through obscurity)
# Change this to a unique random string for your instance
UPLOAD_SUBDOMAIN = 'your-secret-subdomain-here'

def is_upload_subdomain():
    '''Check if request is coming to the upload subdomain'''
    host = request.host.lower()
    return UPLOAD_SUBDOMAIN in host

@app.before_request
def subdomain_protection():
    '''Protect subdomains - return 404 for unauthorized paths'''
    if is_upload_subdomain():
        # Upload subdomain: ONLY allow POST to /api/recording/upload
        if request.path != '/api/recording/upload' or request.method != 'POST':
            logger.warning(f'Blocked request to upload subdomain: {request.method} {request.path} from {request.remote_addr}')
            abort(404)
    else:
        # Dashboard subdomain: BLOCK the upload endpoint
        if request.path == '/api/recording/upload':
            logger.warning(f'Blocked upload attempt to dashboard subdomain from {request.remote_addr}')
            abort(404)

@app.template_filter('format_timestamp')
def format_timestamp(unix_timestamp):
    if not unix_timestamp:
        return 'N/A'
    try:
        from datetime import datetime
        dt = datetime.fromtimestamp(unix_timestamp)
        # Format: 12/21/25 4:14 PM
        return dt.strftime('%m/%d/%y %I:%M %p')
    except:
        return 'N/A'

@app.template_filter('format_duration')
def format_duration(milliseconds):
    if not milliseconds:
        return 'N/A'
    seconds = milliseconds // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    if minutes > 0:
        return f'{minutes}m {seconds}s'
    return f'{seconds}s'

@app.template_filter('format_size')
def format_size(bytes_val):
    if not bytes_val:
        return 'N/A'
    kb = bytes_val / 1024
    if kb < 1024:
        return f'{kb:.2f} KB'
    mb = kb / 1024
    if mb < 1024:
        return f'{mb:.2f} MB'
    gb = mb / 1024
    return f'{gb:.2f} GB'

class UserAuth(UserMixin):
    def __init__(self, user):
        self.id = user.id
        self.username = user.username

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        secret = request.form.get('Secret') or request.form.get('secret') or request.headers.get('X-API-Key')
        if not secret or secret != os.getenv('SECRET_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return UserAuth(user) if user else None

@app.route('/api/recording/upload', methods=['POST'])
@require_api_key
def upload_recording():
    try:
        logger.info(f"ACR Upload - All form fields: {dict(request.form)}")
        source = request.form.get('Source') or request.form.get('source')
        if not source:
            return jsonify({'error': 'Source required'}), 400
        
        original_filename = None        
        if 'File' in request.files or 'file' in request.files:            
            uploaded_file = request.files.get('File') or request.files.get('file')            
            if uploaded_file and uploaded_file.filename:                
                original_filename = uploaded_file.filename
        
        note = request.form.get('Note') or request.form.get('note') or ''
        # URL decode the note (ACR sends URL-encoded text)
        from urllib.parse import unquote_plus
        if note:
            note = unquote_plus(note)
        date_val = request.form.get('Date') or request.form.get('date')
        duration = request.form.get('Duration') or request.form.get('duration')
        if date_val:
            date_val = int(date_val)
        if duration:
            duration = int(duration)
        
        caller_name = None        
        manual_phone = None
        call_direction = None
        if original_filename:            
            import re
            # Extract direction
            direction_match = re.search(r'(Incoming|Outgoing)', original_filename, re.IGNORECASE)
            if direction_match:
                call_direction = direction_match.group(1).capitalize()
            
            # Extract phone number (always try, even without name)
            phone_match = re.search(r'(\+?\d{10,})', original_filename)
            if phone_match:
                phone_num = phone_match.group(1)
                if not phone_num.startswith('+'):
                    phone_num = '+1' + phone_num
                if len(phone_num) >= 11:
                    manual_phone = f"{phone_num[:2]}-{phone_num[2:5]}-{phone_num[5:8]}-{phone_num[8:]}"
            
            # Extract name - try multiple patterns
            name_match1 = re.search(r'^(.+?)\s*\(\+\d', original_filename)
            name_match2 = re.search(r'^([^_\d]+)', original_filename)
            
            if name_match1:
                potential_name = name_match1.group(1).strip(' ()')
                # Check if just a phone number display (only digits/spaces/dashes/parens)
                if re.match(r'^[\d\s\-()]+$', potential_name):
                    caller_name = 'N/A'
                else:
                    caller_name = potential_name
            elif name_match2 and len(name_match2.group(1)) > 1:
                potential_name = name_match2.group(1).strip(' _-')
                if re.match(r'^[\d\s\-()]+$', potential_name):
                    caller_name = 'N/A'
                else:
                    caller_name = potential_name
            elif manual_phone:
                caller_name = 'N/A'
        
        # Initialize variables that may or may not be set
        saved_filename = None
        filesize = None
        
        if 'File' in request.files or 'file' in request.files:
            file = request.files.get('File') or request.files.get('file')
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                saved_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
                file.save(filepath)
                filesize = os.path.getsize(filepath)
        
        recording = Recording(
            source=source, 
            filename=saved_filename, 
            original_filename=original_filename, 
            note=note, 
            date=date_val, 
            filesize=filesize, 
            duration=duration, 
            remote_ip=request.remote_addr,
            caller_name=caller_name,
            manual_phone=manual_phone,
            call_direction=call_direction
        )
        db.session.add(recording)
        db.session.commit()
        return jsonify({'success': True, 'id': recording.id}), 200
    except Exception as e:
        logger.error(f"Upload error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed'}), 500

@app.route('/api/recordings', methods=['GET'])
def get_recordings():
    try:
        recordings = Recording.query.order_by(Recording.created_at.desc()).all()
        return jsonify([r.to_dict() for r in recordings]), 200
    except:
        return jsonify({'error': 'Failed'}), 500

@app.route('/api/recording/<int:recording_id>/note', methods=['GET'])
@login_required
def get_recording_note(recording_id):
    try:
        recording = Recording.query.get_or_404(recording_id)
        return jsonify({'note': recording.note or ''}), 200
    except:
        return jsonify({'error': 'Failed'}), 500

@app.route('/', methods=['GET'])
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    recordings = Recording.query.order_by(Recording.created_at.desc()).paginate(page=page, per_page=20)
    total_recordings = Recording.query.count()
    total_size = sum([r.filesize or 0 for r in Recording.query.all()])
    total_duration = sum([r.duration or 0 for r in Recording.query.all()])
    stats = {
        'total_recordings': total_recordings,
        'total_size': total_size,
        'total_duration': total_duration
    }
    return render_template('index.html', recordings=recordings, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(UserAuth(user))
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/download/<int:recording_id>')
@login_required
def download_recording(recording_id):
    recording = Recording.query.get_or_404(recording_id)
    if not recording.filename:
        return jsonify({'error': 'No file'}), 404
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], recording.filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=recording.original_filename or recording.filename)

@app.route('/play/<int:recording_id>')
@login_required
def play_recording(recording_id):
    recording = Recording.query.get_or_404(recording_id)
    if not recording.filename:
        return jsonify({'error': 'No file'}), 404
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], recording.filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Not found'}), 404
    return send_file(filepath, mimetype='audio/mpeg')

@app.route('/api/recording/<int:recording_id>', methods=['DELETE'])
@login_required
def delete_recording(recording_id):
    try:
        recording = Recording.query.get_or_404(recording_id)
        if recording.filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], recording.filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        db.session.delete(recording)
        db.session.commit()
        return jsonify({'success': True}), 200
    except:
        return jsonify({'error': 'Failed'}), 500

@app.route('/edit/<int:recording_id>', methods=['GET', 'POST'])
@login_required
def edit_recording(recording_id):
    recording = Recording.query.get_or_404(recording_id)
    if request.method == 'POST':
        recording.caller_name = request.form.get('caller_name', '').strip()
        recording.manual_phone = request.form.get('manual_phone', '').strip()
        recording.note = request.form.get('note', '').strip()
        db.session.commit()
        flash('Recording updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit.html', recording=recording)


@app.route('/sync-contacts', methods=['POST'])
@login_required
def sync_contacts():
    """Sync contact names from newer recordings to older ones with the same phone number"""
    try:
        # Get all unique phone numbers with their most recent contact name
        phone_contacts = {}
        
        # Get all recordings ordered by date (newest first)
        all_recordings = Recording.query.order_by(Recording.created_at.desc()).all()
        
        for rec in all_recordings:
            if rec.manual_phone and rec.caller_name and rec.caller_name != 'N/A':
                # Store the first (newest) contact name we find for each phone
                if rec.manual_phone not in phone_contacts:
                    phone_contacts[rec.manual_phone] = rec.caller_name
        
        # Now update older recordings with N/A to use the contact name
        updated = 0
        for rec in all_recordings:
            if rec.manual_phone and rec.caller_name == 'N/A':
                # Check if we have a contact name for this phone number
                if rec.manual_phone in phone_contacts:
                    rec.caller_name = phone_contacts[rec.manual_phone]
                    updated += 1
        
        db.session.commit()
        
        flash(f'Successfully synced contacts! Updated {updated} recordings.', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        logger.error(f'Contact sync error: {e}')
        flash('Error syncing contacts. Check logs.', 'error')
        return redirect(url_for('dashboard'))

def cleanup_old_recordings():
    retention_days = int(os.getenv('RETENTION_DAYS', 365))
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    old = Recording.query.filter(Recording.created_at < cutoff).all()
    for r in old:
        if r.filename:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], r.filename))
            except:
                pass
        db.session.delete(r)
    db.session.commit()

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password_hash=generate_password_hash(os.getenv('WEB_PASSWORD', 'admin')))
        db.session.add(admin)
        db.session.commit()
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_old_recordings, 'cron', hour=2, minute=0)
    scheduler.start()

app.run(host='0.0.0.0', port=5000)