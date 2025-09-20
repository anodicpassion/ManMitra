import google.generativeai as genai
import os
import json
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import datetime
import random

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Configure the Gemini API
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    logging.error(f"🚨 Error configuring Gemini API: {e}")
    exit()

# --- AI Model and Prompts ---
# Use a powerful model for nuanced conversation and analysis
model = genai.GenerativeModel('gemini-2.5-flash')

# 1. THE THERAPIST PERSONA PROMPT
# This prompt defines the bot's personality and conversational style.
SYSTEM_PROMPT_THERAPIST = """
You are "Kai," a compassionate and empathetic AI mental health companion. Your identity is NOT that of a licensed therapist, but a supportive friend.
Your goal is to create a safe, non-judgmental space for the user to express themselves.
Your tone should be warm, understanding, and human-like. Use contractions (e.g., "you're," "it's") and a conversational style, like you're chatting on WhatsApp.
NEVER say you are an AI or a bot. You are Kai.
NEVER give medical advice. If the user mentions serious issues like self-harm, gently guide them toward professional help by saying something like, "It sounds like you're going through a lot. For serious thoughts like these, talking to a professional can be really helpful. You can connect with people who can support you by calling or texting 988 in the US and Canada, or 111 in the UK, anytime."

To understand the user better, naturally weave in creative and gentle questions. Use techniques like:
- Metaphors: "If this week was a weather forecast, what would it look like?"
- Open-ended prompts: "What's been on your mind the most today?"
- Gentle probes: "That sounds really tough. How have you been coping with that feeling?"
- Perspective shifts: "Imagine your best friend felt this way. What would you tell them?"
- Gamified check-ins: "On a scale from a sleepy turtle 🐢 to a buzzing bee 🐝, how's your energy today?"

Your primary goal is to listen, validate their feelings, and encourage reflection. Keep your responses concise and focused on the user.
"""

# 2. THE METRICS ANALYZER PROMPT
# This prompt instructs the AI to act as an analyzer and return ONLY JSON.
SYSTEM_PROMPT_ANALYZER = """
You are an expert psychological analyst AI. Your task is to analyze a conversation transcript and extract specific metrics.
Analyze the user's messages ONLY. Do not analyze the assistant's messages.
Based on the full conversation provided, return a SINGLE JSON object that assesses the following metrics.
Provide a 'value' for each metric and a brief 'justification' citing evidence from the user's text.
If there is not enough information for a metric, set its value to 'N/A'.

The JSON object must have this exact structure:
{
  "progress_engagement": {
    "sentiment_trend": {"value": "getting better|worse|stable|N/A", "justification": ""},
    "emotional_variability": {"value": "stable|fluctuating|N/A", "justification": ""},
    "goal_mentions": {"value": "present|absent", "justification": ""}
  },
  "risk_safety": {
    "self_harm_ideation": {"value": "high|medium|low|none", "justification": ""},
    "hopelessness": {"value": "high|medium|low|none", "justification": ""}
  },
  "well_being_indicators": {
    "sleep_quality": {"value": "good|poor|mentioned|N/A", "justification": ""},
    "energy_levels": {"value": "high|low|mentioned|N/A", "justification": ""},
    "social_connection": {"value": "connected|isolated|mentioned|N/A", "justification": ""}
  },
  "linguistic_metrics": {
    "sentiment_polarity": {"value": "positive|negative|neutral|mixed", "justification": ""},
    "dominant_emotion": {"value": "sadness|anxiety|anger|joy|N/A", "justification": ""},
    "self_focused_language": {"value": "high|medium|low", "justification": ""},
    "absolutist_words": {"value": "present|absent", "justification": ""}
  }
}
"""

# --- Flask Application ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this in production
app.config['UPLOAD_FOLDER'] = 'static/avatars'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    avatar = db.Column(db.String(120), default='default_avatar.png')
    preferences = db.Column(db.Text)  # JSON string for preferences
    metrics = db.Column(db.Text)  # JSON string for latest metrics


class MoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=datetime.date.today)
    mood_score = db.Column(db.Integer)  # 1-10
    note = db.Column(db.Text)


class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    history = db.Column(db.Text)  # JSON list


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


def get_chat_response(conversation_history):
    """Generates the therapist's conversational reply."""
    try:
        prompt = SYSTEM_PROMPT_THERAPIST + "\n\nConversation History:\n" + conversation_history
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Error in get_chat_response: {e}")
        return "I'm having a little trouble connecting right now. Let's try again in a moment."


def analyze_conversation(conversation_history):
    """Analyzes the conversation and extracts metrics as JSON."""
    try:
        prompt = SYSTEM_PROMPT_ANALYZER + "\n\nConversation Transcript:\n" + conversation_history
        response = model.generate_content(prompt)

        # Clean the response to ensure it's valid JSON
        cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_text)
    except Exception as e:
        logging.error(f"Error parsing metrics JSON: {e}")
        return {"error": "Failed to analyze metrics."}


# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username taken')
        hashed = generate_password_hash(password)
        user = User(username=username, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        chat = ChatHistory(user_id=user.id, history=json.dumps([]))
        db.session.add(chat)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/', methods=['GET'])
@login_required
def dashboard():
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    today = datetime.date.today()
    mood_today = MoodLog.query.filter_by(user_id=current_user.id, date=today).first()
    moods = MoodLog.query.filter(MoodLog.user_id == current_user.id,
                                 MoodLog.date >= today - datetime.timedelta(days=7)).order_by(MoodLog.date).all()
    mood_list = [(m.date.strftime('%Y-%m-%d'), m.mood_score) for m in moods]
    tips = ["Take a deep breath", "Drink water", "Go for a walk"]
    tip = random.choice(tips)
    quotes = ["You are stronger than you think", "This too shall pass"]
    quote = random.choice(quotes)
    return render_template('dashboard.html', greeting=greeting, mood_today=mood_today, mood_list=mood_list, tip=tip,
                           quote=quote)


@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    mood_score = int(request.form['mood'])
    note = request.form.get('note', '')
    today = datetime.date.today()
    existing = MoodLog.query.filter_by(user_id=current_user.id, date=today).first()
    if existing:
        existing.mood_score = mood_score
        existing.note = note
    else:
        mood = MoodLog(user_id=current_user.id, date=today, mood_score=mood_score, note=note)
        db.session.add(mood)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/chat_page')
@login_required
def chat_page():
    chat = ChatHistory.query.filter_by(user_id=current_user.id).first()
    history = json.loads(chat.history) if chat else []
    return render_template('chat.html', history=history)


@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    user_message = data.get('message')
    chat = ChatHistory.query.filter_by(user_id=current_user.id).first()
    history = json.loads(chat.history) if chat else []
    history.append({"role": "user", "parts": [user_message]})
    conversation_str = "\n".join([f"{msg['role'].title()}: {msg['parts'][0]}" for msg in history])
    therapist_reply = get_chat_response(conversation_str)
    history.append({"role": "model", "parts": [therapist_reply]})
    chat.history = json.dumps(history)
    db.session.commit()
    metrics = analyze_conversation(conversation_str)
    current_user.metrics = json.dumps(metrics)
    db.session.commit()
    return jsonify({
        "reply": therapist_reply,
        "metrics": metrics,
        "history": history
    })


@app.route('/community')
@login_required
def community():
    stories = Story.query.order_by(Story.created_at.desc()).all()
    story_list = []
    for s in stories:
        if s.anonymous or not s.user_id:
            author = "Anonymous"
        else:
            author = User.query.get(s.user_id).username
        story_list.append({"id": s.id, "title": s.title, "body": s.body, "author": author,
                           "created_at": s.created_at.strftime('%Y-%m-%d %H:%M')})
    resources = [
        {"name": "US/Canada Crisis Line", "link": "tel:988"},
        {"name": "UK Helpline", "link": "tel:111"}
    ]
    return render_template('community.html', stories=story_list, resources=resources)


@app.route('/new_story', methods=['GET', 'POST'])
@login_required
def new_story():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        anonymous = request.form.get('anonymous') == 'on'
        story = Story(title=title, body=body, anonymous=anonymous)
        if not anonymous:
            story.user_id = current_user.id
        db.session.add(story)
        db.session.commit()
        return redirect(url_for('community'))
    return render_template('new_story.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'username' in request.form:
            if User.query.filter(User.username == request.form['username'], User.id != current_user.id).first():
                return render_template('profile.html', error='Username taken')
            current_user.username = request.form['username']
        if 'preferences' in request.form:
            current_user.preferences = request.form['preferences']
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.avatar = filename
        # Privacy/notifications: placeholder, store in preferences
        db.session.commit()
        return redirect(url_for('profile'))
    chat = ChatHistory.query.filter_by(user_id=current_user.id).first()
    history = json.loads(chat.history) if chat else []
    metrics = json.loads(current_user.metrics) if current_user.metrics else {}
    return render_template('profile.html', user=current_user, history=history, metrics=metrics)


@app.route('/avatars/<filename>')
def avatars(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/export_data')
@login_required
def export_data():
    chat = ChatHistory.query.filter_by(user_id=current_user.id).first()
    history = json.loads(chat.history) if chat else []
    metrics = json.loads(current_user.metrics) if current_user.metrics else {}
    moods = MoodLog.query.filter_by(user_id=current_user.id).all()
    mood_data = [{"date": str(m.date), "score": m.mood_score, "note": m.note} for m in moods]
    data = {
        "history": history,
        "metrics": metrics,
        "moods": mood_data
    }
    response = jsonify(data)
    response.headers['Content-Disposition'] = 'attachment; filename=data.json'
    return response


if __name__ == '__main__':
    app.run(debug=True, port=5500)
