
# 🎣 ACR Phone Hooker

A powerful Flask-based call recording management system for [ACR Phone](https://nllapps.com/apps/cb/default.htm). Automatically receive, store, and manage call recordings from your Android device with a beautiful web dashboard.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-green)
![Flask](https://img.shields.io/badge/flask-3.0%2B-lightblue)

## Features

### 🎙️ Core Recording Management
- **Automatic Recording Upload**: Receive call recordings directly from ACR Phone app
- **Audio Storage**: Store audio files in MP3, M4A, WAV, OGG, FLAC, and more
- **Metadata Extraction**: Automatically parse contact info, phone numbers, and call direction
- **Call Direction Detection**: Distinguish between incoming and outgoing calls
- **Automatic Cleanup**: Delete recordings older than 365 days (configurable)

### 📱 Web Dashboard
- **Beautiful UI**: Modern, responsive design with light/dark mode
- **Mobile Optimized**: Fully responsive for phones, tablets, and desktops
- **Search & Filter**: Find recordings by contact name or phone number
- **Call Analytics**: View total recordings, storage size, and duration stats
- **Contact Management**: Edit caller names and phone numbers manually
- **Notes**: Add and view notes on individual calls

### 🔐 Security & Privacy
- **Authentication**: Web dashboard login with username/password
- **API Key Protection**: Secure webhook endpoint with secret key
- **Obscure Subdomain**: Optional security-through-obscurity for upload endpoint
- **Data Privacy**: All recordings stored locally, never sent to third parties

### 🚀 Deployment Ready
- **Systemd Service**: Runs as background service with auto-restart
- **Cloudflare Tunnel**: Optional remote access via Cloudflare
- **Split DNS**: Local and remote access with intelligent routing
- **SQLite Database**: No external database dependencies

## Quick Start

### Prerequisites
- Python 3.9+
- pip and venv
- 100MB+ free disk space for recordings

### Installation

1. **Clone this repository**:
```bash
git clone https://github.com/Mr-Renegade/acr-phone-hooker.git
cd acr-phone-hooker
```

2. **Create Python virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings:
# - Generate SECRET_KEY: openssl rand -hex 32
# - Set WEB_PASSWORD to a strong password
# - Configure UPLOAD_FOLDER to your desired location
```

5. **Initialize database**:
```bash
python app.py
```
The app will create the database and admin user on first run.

6. **Access the dashboard**:
- **Local**: http://localhost:5000
- **Remote**: https://your-domain.com (if configured)
- **Login**: admin / (password from .env)

### ACR Phone Configuration

1. Open **ACR Phone** app
2. Go to **Settings** → **Call Reporting**
3. Configure:
   - **Server URL**: `https://your-domain.com/api/recording/upload` (replace with your domain)
   - **Secret**: (copy SECRET_KEY from .env)
   - **Send recording file**: ✓ Yes
   - **Send on**: WiFi and Mobile Data (or WiFi only)

4. Make a test call - it should appear in the dashboard within seconds!

## Project Structure

```
acr-phone-hooker/
├── app.py                 # Main Flask application
├── models.py              # Database models (SQLAlchemy)
├── requirements.txt       # Python dependencies
├── .env                   # Configuration (keep secret!)
├── data/
│   └── recordings.db      # SQLite database
├── uploads/               # Audio recording files
├── templates/
│   ├── base.html          # Base template with header/footer
│   ├── index.html         # Dashboard page
│   ├── edit.html          # Edit recording details
│   └── login.html         # Login page
└── logs/                  # Application logs
```

## Configuration

### Environment Variables (.env)

```bash
# Flask Settings
SECRET_KEY=your-secret-key-here              # 32-char hex string
FLASK_HOST=0.0.0.0                          # Bind to all interfaces
FLASK_PORT=5000                             # Port number
FLASK_DEBUG=False                           # Never enable in production!

# Database
DATABASE_URL=sqlite:////path/to/your/data/recordings.db

# Upload Settings
UPLOAD_FOLDER=/path/to/your/uploads         # Where to store audio files
MAX_UPLOAD_SIZE_MB=100                      # Max file size

# Web Interface
WEB_USERNAME=admin                          # Dashboard username
WEB_PASSWORD=strong-password-here           # Dashboard password

# Retention Policy
RETENTION_DAYS=365                          # Auto-delete after N days

# Logging
LOG_LEVEL=INFO                              # DEBUG, INFO, WARNING, ERROR
```

## API Reference

### Upload Recording
```
POST /api/recording/upload
Content-Type: multipart/form-data

Parameters:
  Source (required)    - Phone number or contact name
  File (optional)      - Audio file
  Secret (required)    - API secret key
  Date (optional)      - Unix timestamp
  Duration (optional)  - Duration in milliseconds
  Note (optional)      - Call notes
```

### Get Recordings
```
GET /api/recordings
Authorization: Login required

Returns: JSON array of all recordings
```

### Delete Recording
```
DELETE /api/recording/{id}
Authorization: Login required

Returns: Success message
```

### Get Recording Note
```
GET /api/recording/{id}/note
Authorization: Login required

Returns: JSON with note content
```

## Features in Detail

### Contact Sync
Automatically update old recordings with contact information from newer calls:
- Click **"Sync Contacts"** button
- Matches phone numbers and updates caller names
- Useful when contacts are added after calls are recorded

### Notes
Add personal notes to call recordings:
- Click **edit icon** to open recording details
- Add note in the Notes field
- Save changes
- Click **note icon** to view later

### Dark Mode
Toggle between light and dark themes:
- Click **sun/moon icon** in header
- Preference saved to browser

### Mobile View
Full responsive design:
- Works on phones (360px+)
- Optimized touch targets
- Card-based table layout on mobile
- Collapsible sections

## Deployment Options

### Local Network
```bash
# Run Flask development server
python app.py

# Or use Gunicorn in production
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### With Systemd Service
```bash
# Create /etc/systemd/system/acr-phone-hooker.service
sudo systemctl enable acr-phone-hooker
sudo systemctl start acr-phone-hooker
sudo systemctl status acr-phone-hooker
```

### With Cloudflare Tunnel
Expose to the internet securely without port forwarding:

```bash
# Install cloudflared
# Configure tunnel to point to localhost:5000
# Access via https://phone.example.com
```

## Data Backup

It's recommended to regularly backup your call recordings and database. Here's how:

### Manual Backup
```bash
# Create a backup of all data
tar -czf acr-phone-hooker-backup-$(date +%Y%m%d).tar.gz \
  data/ \
  uploads/

# For a complete backup including configuration:
tar -czf acr-phone-hooker-full-$(date +%Y%m%d).tar.gz \
  data/ \
  uploads/ \
  .env \
  app.py models.py requirements.txt \
  templates/
```

### Restore from Backup
```bash
# Extract backup to restore your data
tar -xzf acr-phone-hooker-backup-YYYYMMDD.tar.gz
```

### Automated Backups
Consider setting up a cron job for automatic daily/weekly backups:
```bash
# Add to crontab (crontab -e)
# Daily backup at 2 AM
0 2 * * * tar -czf /backup/acr-phone-hooker-$(date +\%Y\%m\%d).tar.gz /path/to/data /path/to/uploads
```

**Note**: Keep backups in a secure location. If storing on external systems, consider encrypting sensitive data.

## Troubleshooting

### 500 Error on Upload
- **Check**: ACR Phone secret matches SECRET_KEY in .env
- **Check**: Upload folder exists and has write permissions
- **Check**: Disk space available
- **Check**: Service logs: `journalctl -u acr-phone-hooker -f`

### Can't Access Dashboard
- **Local**: Check firewall allows port 5000
- **Remote**: Check Cloudflare tunnel status
- **Mobile**: Check WiFi/4G connectivity
- **Login**: Verify WEB_USERNAME/WEB_PASSWORD in .env

### Recordings Not Uploading
- **Check**: ACR Phone settings have correct server URL
- **Check**: Secret key is correctly entered in ACR Phone
- **Check**: "Send recording file" option is enabled
- **Check**: Network connectivity

### Database Locked
- **Solution**: Stop service and restart
```bash
sudo systemctl stop acr-phone-hooker
sudo systemctl start acr-phone-hooker
```

## Performance

- **Typical Upload**: 5-10 seconds for 5MB file
- **Dashboard Load**: <500ms with 1000 recordings
- **Concurrent Users**: 10+ simultaneous users supported
- **Storage**: ~5-10 MB per call recording (varies by quality)

## Security Considerations

1. **Keep .env Private**: Never commit to git or share
2. **Use HTTPS**: Always use HTTPS in production
3. **Change Passwords**: Set strong WEB_PASSWORD
4. **Firewall**: Only expose via Cloudflare or private network
5. **Regular Backups**: Keep encrypted backups in secure location
6. **Update Dependencies**: Regularly run `pip install --upgrade -r requirements.txt`

## Future Roadmap

See [Feature Ideas](./FEATURE_IDEAS.md) for planned enhancements:
- Call transcription with Whisper AI
- Advanced search and analytics
- Bulk actions and exports
- Slack/Discord notifications
- Mobile app integration

## Contributing

Contributions welcome! Please:
1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Ask questions on GitHub Discussions
- **ACR Phone Docs**: https://nllapps.com/apps/cb/help-call-reporting.htm

## Acknowledgments

- [ACR Phone](https://nllapps.com/) - Original call recording app
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Cloudflare](https://www.cloudflare.com/) - Tunnel & DNS

---

Made with 💙 for call recording enthusiasts and privacy advocates.
