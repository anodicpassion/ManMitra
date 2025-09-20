from flask import Flask, render_template, request, redirect, url_for, make_response
import os
import glob
import random
import json
import csv
from datetime import date
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/avatars'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='default.png')
    preferences = db.Column(db.Text, default='{}')  # JSON string for settings


class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    anonymous = db.Column(db.Boolean, default=False)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    mood = db.Column(db.Integer, nullable=False)  # 1-5 scale


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Get all HTML files from the stitch_journaling_dashboard directory
def get_html_files():
    html_files = []
    dashboard_path = os.path.join(os.path.dirname(__file__), 'stitch_journaling_dashboard')

    # Find all code.html files recursively
    for root, dirs, files in os.walk(dashboard_path):
        for file in files:
            if file == 'code.html':
                # Get the relative path from dashboard directory
                rel_path = os.path.relpath(root, dashboard_path)
                # Create a route name from the directory name
                route_name = rel_path.replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '').replace('&',
                                                                                                                    'and').replace(
                    '-', '_').lower()
                html_files.append({
                    'route_name': route_name,
                    'file_path': os.path.join(root, file),
                    'display_name': rel_path.replace('_', ' ').title()
                })

    return html_files


# Get all HTML files
html_files = get_html_files()


@app.route('/')
def index():
    """Home page with navigation to all screens"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html', screens=html_files)


@app.route('/dashboard')
@login_required
def dashboard():
    """Main journaling dashboard"""
    greeting = f"Hello, {current_user.username}! How are you feeling today?"

    # Mood summary progress
    moods = Mood.query.filter_by(user_id=current_user.id).order_by(Mood.date.desc()).limit(7).all()
    mood_summary = [m.mood for m in moods]
    dates = [m.date.strftime('%Y-%m-%d') for m in moods]
    chart = "Mood Progress (last 7 days):\n" + "\n".join([f"{d}: {m}" for d, m in zip(dates, mood_summary)])

    # Daily tips and motivational quote
    tips = ["Stay hydrated!", "Take a short walk.", "Practice deep breathing.", "Journal your thoughts."]
    quotes = ["You are stronger than you think.", "Every day is a new beginning.", "Believe in yourself."]
    daily_tip = random.choice(tips)
    motivational_quote = random.choice(quotes)

    return render_template('stitch_journaling_dashboard/journaling_dashboard_4/code.html',
                           greeting=greeting, chart=chart, daily_tip=daily_tip, quote=motivational_quote)


@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    """Handle daily check-in mood submission"""
    mood = int(request.form.get('mood', 3))  # Default to 3 if not provided
    today = date.today()
    existing = Mood.query.filter_by(user_id=current_user.id, date=today).first()
    if existing:
        existing.mood = mood
    else:
        new_mood = Mood(user_id=current_user.id, mood=mood)
        db.session.add(new_mood)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login/signup screen"""
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')

        if action == 'signup':
            if User.query.filter_by(username=username).first():
                # Username taken, handle error in template
                return render_template('stitch_journaling_dashboard/login/signup_screen_1/code.html',
                                       error="Username taken")
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))

        elif action == 'login':
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                return render_template('stitch_journaling_dashboard/login/signup_screen_1/code.html',
                                       error="Invalid credentials")

    return render_template('stitch_journaling_dashboard/login/signup_screen_1/code.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/ai-chat', methods=['GET', 'POST'])
@login_required
def ai_chat():
    """AI companion chat"""
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            user_msg = ChatMessage(user_id=current_user.id, message=message, is_user=True)
            db.session.add(user_msg)
            # Simple mock AI response
            responses = ["I understand. Tell me more.", "That's interesting. How does that make you feel?",
                         "Remember to be kind to yourself."]
            ai_response = random.choice(responses)
            ai_msg = ChatMessage(user_id=current_user.id, message=ai_response, is_user=False)
            db.session.add(ai_msg)
            db.session.commit()

    history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    return render_template('stitch_journaling_dashboard/ai_companion_chat_screen_1/code.html', history=history)


@app.route('/peer-support', methods=['GET', 'POST'])
@login_required
def peer_support():
    """Peer support forum"""
    if request.method == 'POST':
        title = request.form.get('title')
        body = request.form.get('body')
        anonymous = request.form.get('anonymous') == 'on'
        new_story = Story(title=title, body=body, user_id=current_user.id, anonymous=anonymous)
        db.session.add(new_story)
        db.session.commit()

    stories = Story.query.order_by(Story.id.desc()).all()
    story_data = []
    for story in stories:
        author = "Anonymous" if story.anonymous else (
            User.query.get(story.user_id).username if story.user_id else "Anonymous")
        story_data.append({'title': story.title, 'body': story.body, 'author': author})

    resources = [
        {'name': 'National Suicide Prevention Lifeline', 'link': 'https://988lifeline.org/',
         'description': 'Call 988 for 24/7 support'},
        {'name': 'Crisis Text Line', 'link': 'https://www.crisistextline.org/', 'description': 'Text HOME to 741741'},
        {'name': 'National Alliance on Mental Illness', 'link': 'https://www.nami.org/',
         'description': 'Resources and support'}
    ]

    return render_template('stitch_journaling_dashboard/peer_support_forum_1/code.html', stories=story_data,
                           resources=resources)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Settings page"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            new_username = request.form.get('username')
            if new_username and new_username != current_user.username:
                if not User.query.filter_by(username=new_username).first():
                    current_user.username = new_username
                    db.session.commit()

        elif action == 'upload_avatar':
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    current_user.avatar = filename
                    db.session.commit()

        elif action == 'update_preferences':
            # Example: privacy and notifications
            privacy = request.form.get('privacy', 'public')
            notifications = request.form.get('notifications', 'on')
            prefs = json.loads(current_user.preferences)
            prefs['privacy'] = privacy
            prefs['notifications'] = notifications
            current_user.preferences = json.dumps(prefs)
            db.session.commit()

    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    preferences = json.loads(current_user.preferences)

    return render_template('stitch_journaling_dashboard/account_settings_screen_2/code.html',
                           user=current_user, chat_history=chat_history, preferences=preferences)


@app.route('/export')
@login_required
def export():
    """Data export/download option"""
    output = []
    output.append(['Type', 'Date/Time', 'Details'])

    # Moods
    moods = Mood.query.filter_by(user_id=current_user.id).order_by(Mood.date).all()
    for mood in moods:
        output.append(['Mood', mood.date.strftime('%Y-%m-%d'), str(mood.mood)])

    # Chat history
    chats = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    for chat in chats:
        sender = 'User' if chat.is_user else 'AI'
        output.append(['Chat', chat.timestamp.strftime('%Y-%m-%d %H:%M:%S'), f"{sender}: {chat.message}"])

    # Stories (only user's own)
    stories = Story.query.filter_by(user_id=current_user.id).all()
    for story in stories:
        output.append(['Story', '', f"Title: {story.title}, Body: {story.body}, Anonymous: {story.anonymous}"])

    si = '\n'.join(','.join(map(str, row)) for row in output)
    response = make_response(si)
    response.headers["Content-Disposition"] = "attachment; filename=user_data_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response


# Dynamic routes for all other screens
for html_file in html_files:
    route_name = html_file['route_name']
    file_path = html_file['file_path']

    # Skip the ones we already defined above
    if route_name in ['journaling_dashboard_4', 'login_signup_screen_1', 'ai_companion_chat_screen_1',
                      'peer_support_forum_1', 'account_settings_screen_2']:
        continue


    # Create route function dynamically
    def make_route_handler(file_path):
        def route_handler():
            template_path = file_path.replace(
                os.path.join(os.path.dirname(__file__), 'stitch_journaling_dashboard') + os.sep,
                'stitch_journaling_dashboard/')
            return render_template(template_path)

        return route_handler


    # Add the route with login required
    app.add_url_rule(f'/{route_name}', route_name, login_required(make_route_handler(file_path)))


# Navigation helper routes
@app.route('/navigate/<screen_name>')
def navigate(screen_name):
    """Navigate to any screen by name"""
    for html_file in html_files:
        if html_file['route_name'] == screen_name:
            return redirect(url_for(html_file['route_name']))
    return redirect(url_for('index'))


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5500)