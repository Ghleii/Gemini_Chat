from prompts import get_initial_prompt, get_prompt
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo
import os
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///gemini_chat.db")

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return render_template('register.html', form=form)

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/initial_message', methods=['GET'])
@login_required
def initial_message():
    try:
        initial_prompt = get_initial_prompt()
        response = model.start_chat().send_message(initial_prompt)
        
        # 会話履歴を更新
        conversation_history = [{
            'role': 'assistant',
            'content': response.text
        }]
        session['conversation_history'] = conversation_history
        
        return jsonify({'response': response.text})
    except Exception as e:
        app.logger.error(f"Error in initial_message: {str(e)}")
        return jsonify({'error': 'Unable to get initial message'}), 500

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.get_json()
        csrf_token = data.get('csrf_token')
        if not csrf.validate_csrf(csrf_token):
            return jsonify({'error': 'CSRF token is missing or invalid'}), 400

        user_message = data['message']
        conversation_history = session.get('conversation_history', [])

        full_prompt = get_prompt(user_message, conversation_history)

        # Gemini APIへのリクエスト
        chat = model.start_chat(history=[
            {"role": "user" if item['role'] == 'human' else "model", "parts": [item['content']]}
            for item in conversation_history
        ])
        response = chat.send_message(full_prompt)

        # 会話履歴の更新
        conversation_history.append({'role': 'human', 'content': user_message})
        conversation_history.append({'role': 'assistant', 'content': response.text})
        session['conversation_history'] = conversation_history

        return jsonify({'response': response.text})

    except Exception as e:
        app.logger.error(f"Error in chat: {str(e)}")
        return jsonify({'error': 'Unable to get response from server'}), 500

# 他のルートも@login_requiredデコレータを追加

# デバック
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)