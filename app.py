from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth

load_dotenv()

# OpenAI & OpenRouter Clients
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai-api-key")
or_api_key = os.getenv("OPENROUTER_API_KEY")

client = None
if api_key:
    client = OpenAI(api_key=api_key)

or_client = None
if or_api_key:
    or_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=or_api_key,
        default_headers={
            "HTTP-Referer": "http://localhost:5000", # Required by OpenRouter
            "X-Title": "Study Planner",
        }
    )

def get_ai_client(model_name):
    # If model starts with openrouter prefix or is not an openai model
    if "/" in model_name or (or_client and not client):
        return or_client or client
    return client or or_client

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyplanner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_active = db.Column(db.Date)
    preferred_model = db.Column(db.String(100), default='google/gemini-2.0-flash-001')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class StudyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    goal = db.Column(db.Text, nullable=False)
    timeframe = db.Column(db.String(100))
    project_type = db.Column(db.String(100))
    content = db.Column(db.Text)
    completed_tasks = db.Column(db.JSON, default=list) # List of completed task indices
    is_public = db.Column(db.Boolean, default=False)
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('plans', lazy=True))
    
    # Social stats
    fork_count = db.Column(db.Integer, default=0)
    original_plan_id = db.Column(db.Integer, db.ForeignKey('study_plan.id'), nullable=True)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('study_plan.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('study_plan.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Setup logger
handler = RotatingFileHandler('info.log', maxBytes=100000, backupCount=3)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Routes
@app.route('/')
def index():
    plans = []
    if current_user.is_authenticated:
        plans = StudyPlan.query.filter_by(user_id=current_user.id).order_by(StudyPlan.created_at.desc()).limit(3).all()
    return render_template('index.html', plans=plans)

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def google_authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    email = user_info['email']
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Create a new user if they don't exist
        user = User(username=user_info['name'], email=email)
        # OAuth users don't need a password_hash by default
        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('signup'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/study_plan_creator_frontend')
@login_required
def study_plan_creator_frontend():
    return render_template('study_plan_creator_frontend.html')

@app.route('/my_plans')
@login_required
def my_plans():
    plans = StudyPlan.query.filter_by(user_id=current_user.id).order_by(StudyPlan.created_at.desc()).all()
    return render_template('my_plans.html', plans=plans)

@app.route('/public_plans')
def public_plans():
    plans = StudyPlan.query.filter_by(is_public=True).order_by(StudyPlan.created_at.desc()).all()
    return render_template('public_plans.html', plans=plans)

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    model = request.json.get('preferred_model')
    if model:
        current_user.preferred_model = model
        db.session.commit()
    return jsonify({"success": True})

@app.route('/study_plan_creator', methods=['POST'])
@login_required
def study_plan_creator():
    goal = request.form.get('goal')
    timeframe = request.form.get('timeframe')
    project_type = request.form.get('project_type')
    reference_preference = request.form.get('reference_preference')
    is_public = request.form.get('is_public') == 'on'
    selected_model = request.form.get('model') or current_user.preferred_model

    if not all([goal, timeframe, project_type]):
        return jsonify({"error": "Missing required fields"}), 400

    active_client = get_ai_client(selected_model)
    if not active_client:
        return jsonify({"error": "No AI client configured (OpenAI or OpenRouter)."}), 500

    experts = {
        'coding': 'Senior Engineer', 'art': 'Artist', 'art & craft': 'Craftsman',
        'music': 'Musician', 'dance': 'Dancer', 'cooking': 'Chef',
        'photography': 'Photographer', 'writing': 'Author', 'design': 'Designer',
        'marketing': 'Marketing Specialist', 'finance': 'Financial Analyst',
        'science': 'Scientist', 'mathematics': 'Mathematician',
        'history': 'Historian', 'philosophy': 'Philosopher'
    }
    expert = experts.get(project_type, 'General Expert')
    
    system_prompt = f"Suppose you are {expert}. Create a detailed study plan for: {goal}. Timeframe: {timeframe}. Preferences: {reference_preference}."
    query = f"Provide a step-by-step plan with resources for learning {goal} in {timeframe}."

    try:
        response = active_client.chat.completions.create(
            model=selected_model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': query}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        content = response.choices[0].message.content
        
        # Save to DB
        new_plan = StudyPlan(
            title=f"Plan for {goal[:50]}...",
            goal=goal,
            timeframe=timeframe,
            project_type=project_type,
            content=content,
            is_public=is_public,
            user_id=current_user.id
        )
        db.session.add(new_plan)
        update_user_activity(current_user, 50) # 50 XP for creating a plan
        db.session.commit()
        
        return jsonify({"response": content, "plan_id": new_plan.id})
    except Exception as e:
        logger.error(f'Error: {e}')
        return jsonify({"error": str(e)}), 500

@app.route('/toggle_task/<int:plan_id>', methods=['POST'])
@login_required
def toggle_task(plan_id):
    plan = StudyPlan.query.get_or_404(plan_id)
    if plan.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    task_idx = request.json.get('task_idx')
    total_tasks = request.json.get('total_tasks')
    
    completed = list(plan.completed_tasks or [])
    if task_idx in completed:
        completed.remove(task_idx)
    else:
        completed.append(task_idx)
    
    plan.completed_tasks = completed
    
    # Auto-calculate progress
    if total_tasks > 0:
        plan.progress = int((len(completed) / total_tasks) * 100)
    
    update_user_activity(current_user, 5) # 5 XP per task toggle
    db.session.commit()
    return jsonify({"success": True, "progress": plan.progress, "completed": completed})

@app.route('/update_progress/<int:plan_id>', methods=['POST'])
@login_required
def update_progress(plan_id):
    plan = StudyPlan.query.get_or_404(plan_id)
    if plan.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    progress = request.json.get('progress')
    if progress is not None:
        plan.progress = progress
        update_user_activity(current_user, 15) # 15 XP for progress update
        db.session.commit()
    return jsonify({"success": True})

# Helper for Gamification
def update_user_activity(user, xp_gain):
    today = datetime.utcnow().date()
    if user.last_active == today:
        pass # Already active today
    elif user.last_active == today - timedelta(days=1):
        user.streak += 1
    else:
        user.streak = 1
    
    user.last_active = today
    user.xp += xp_gain
    db.session.commit()

from datetime import timedelta

# Social Routes
@app.route('/fork_plan/<int:plan_id>', methods=['POST'])
@login_required
def fork_plan(plan_id):
    original_plan = StudyPlan.query.get_or_404(plan_id)
    new_plan = StudyPlan(
        title=f"Fork of {original_plan.title}",
        goal=original_plan.goal,
        timeframe=original_plan.timeframe,
        project_type=original_plan.project_type,
        content=original_plan.content,
        is_public=False,
        user_id=current_user.id,
        original_plan_id=original_plan.id
    )
    original_plan.fork_count += 1
    db.session.add(new_plan)
    update_user_activity(current_user, 20) # 20 XP for forking
    db.session.commit()
    return jsonify({"success": True, "new_plan_id": new_plan.id})

@app.route('/like_plan/<int:plan_id>', methods=['POST'])
@login_required
def like_plan(plan_id):
    existing_like = Like.query.filter_by(user_id=current_user.id, plan_id=plan_id).first()
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({"success": True, "liked": False})
    
    new_like = Like(user_id=current_user.id, plan_id=plan_id)
    db.session.add(new_like)
    update_user_activity(current_user, 5) # 5 XP for liking
    db.session.commit()
    return jsonify({"success": True, "liked": True})

@app.route('/add_comment/<int:plan_id>', methods=['POST'])
@login_required
def add_comment(plan_id):
    content = request.json.get('content')
    if not content:
        return jsonify({"error": "Comment cannot be empty"}), 400
    
    comment = Comment(content=content, user_id=current_user.id, plan_id=plan_id)
    db.session.add(comment)
    update_user_activity(current_user, 10) # 10 XP for commenting
    db.session.commit()
    return jsonify({"success": True, "username": current_user.username, "content": content})

@app.route('/plan_details/<int:plan_id>')
def plan_details(plan_id):
    plan = StudyPlan.query.get_or_404(plan_id)
    comments = Comment.query.filter_by(plan_id=plan_id).order_by(Comment.created_at.desc()).all()
    likes = Like.query.filter_by(plan_id=plan_id).count()
    is_liked = False
    if current_user.is_authenticated:
        is_liked = Like.query.filter_by(user_id=current_user.id, plan_id=plan_id).first() is not None
    
    return jsonify({
        "title": plan.title,
        "content": plan.content,
        "author": plan.user.username,
        "forks": plan.fork_count,
        "likes": likes,
        "is_liked": is_liked,
        "completed_tasks": plan.completed_tasks or [],
        "comments": [{"username": c.user.username, "content": c.content, "date": c.created_at.strftime('%Y-%m-%d')} for c in comments]
    })

@app.route('/generate_quiz/<int:plan_id>', methods=['POST'])
@login_required
def generate_quiz(plan_id):
    plan = StudyPlan.query.get_or_404(plan_id)
    active_client = get_ai_client(current_user.preferred_model)
    if not active_client:
        return jsonify({"error": "AI client not configured"}), 500

    prompt = f"Based on this study plan content, generate a 5-question multiple-choice quiz with answers at the end:\n\n{plan.content}"
    try:
        response = active_client.chat.completions.create(
            model=current_user.preferred_model,
            messages=[
                {'role': 'system', 'content': "You are an expert tutor. Create a quiz to test the user's knowledge."},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=1000
        )
        update_user_activity(current_user, 15)
        return jsonify({"quiz": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/suggest_resources/<int:plan_id>', methods=['POST'])
@login_required
def suggest_resources(plan_id):
    plan = StudyPlan.query.get_or_404(plan_id)
    roadblock = request.json.get('roadblock', 'none')
    active_client = get_ai_client(current_user.preferred_model)
    
    prompt = f"The student is at {plan.progress}% progress on this plan: '{plan.title}'. They are stuck on: {roadblock}. Suggest 3 specific, high-quality links or resources to help them."
    try:
        response = active_client.chat.completions.create(
            model=current_user.preferred_model,
            messages=[
                {'role': 'system', 'content': "You are a helpful learning assistant."},
                {'role': 'user', 'content': prompt}
            ]
        )
        return jsonify({"suggestions": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reschedule_plan/<int:plan_id>', methods=['POST'])
@login_required
def reschedule_plan(plan_id):
    plan = StudyPlan.query.get_or_404(plan_id)
    active_client = get_ai_client(current_user.preferred_model)
    
    prompt = f"The student has completed {plan.progress}% of this study plan but is struggling to keep up. Re-balance and rewrite the REMAINING steps to be more manageable while keeping the same end goal:\n\n{plan.content}"
    try:
        response = active_client.chat.completions.create(
            model=current_user.preferred_model,
            messages=[
                {'role': 'system', 'content': "You are an expert project manager and tutor."},
                {'role': 'user', 'content': prompt}
            ]
        )
        new_content = response.choices[0].message.content
        plan.content = new_content
        db.session.commit()
        return jsonify({"new_content": new_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)