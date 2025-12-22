from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Recording(db.Model):
    """
    Database model for call recordings
    
    Stores metadata about each call recording including:
    - Source phone number/contact name
    - File information (name, size)
    - Call details (date, duration)
    - Upload information (timestamp, IP)
    """
    __tablename__ = 'recordings'
    
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(200), nullable=False, index=True)  # Phone number or contact name
    filename = db.Column(db.String(500))  # Saved filename on disk
    original_filename = db.Column(db.String(500))  # Original filename from upload
    note = db.Column(db.Text)  # Optional notes about the call
    date = db.Column(db.Integer, index=True)  # Unix timestamp (seconds) when call occurred
    filesize = db.Column(db.Integer)  # File size in bytes
    duration = db.Column(db.Integer)  # Call duration in milliseconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # When uploaded
    remote_ip = db.Column(db.String(50))  # IP address that uploaded the recording

    # Phone lookup information
    phone_valid = db.Column(db.Boolean)  # Whether phone number is valid
    phone_carrier = db.Column(db.String(200))  # Carrier name (e.g., AT&T, Verizon)
    phone_location = db.Column(db.String(200))  # Location/city
    phone_line_type = db.Column(db.String(50))  # mobile, landline, voip, etc.
    phone_country = db.Column(db.String(100))  # Country name
    phone_country_code = db.Column(db.String(10))  # Country code (e.g., US, CA)
    caller_name = db.Column(db.String(200))  # Manually entered caller name (if known)
    manual_phone = db.Column(db.String(50))  # Manually entered phone number (if known)
    call_direction = db.Column(db.String(20))  # Incoming or Outgoing call
    
    def __repr__(self):
        return f'<Recording {self.id}: {self.source} at {self.date}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'source': self.source,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'note': self.note,
            'date': self.date,
            'filesize': self.filesize,
            'duration': self.duration,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'remote_ip': self.remote_ip,
            'caller_name': self.caller_name,
            'manual_phone': self.manual_phone,
            'call_direction': self.call_direction
        }

class User(UserMixin, db.Model):
    """
    Simple user model for web dashboard authentication
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def __repr__(self):
        return f'<User {self.username}>'
