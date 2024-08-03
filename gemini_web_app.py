# gemini_web_app.py
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
import os
from prompts import get_prompt, get_initial_prompt

app = Flask(__name__)
app.secret_key = os.urandom(24)  # セッション管理のための秘密鍵

# Gemini APIの設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

@app.route('/')
def index():
    session['conversation_history'] = []  # 新しいセッションを開始
    return render_template('index.html')

@app.route('/initial_message', methods=['GET'])
def initial_message():
    initial_prompt = get_initial_prompt()
    response = model.start_chat().send_message(initial_prompt)
    
    # 会話履歴を更新
    conversation_history = [{
        'role': 'assistant',
        'content': response.text
    }]
    session['conversation_history'] = conversation_history
    
    return jsonify({'response': response.text})

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    conversation_history = session.get('conversation_history', [])
    
    full_prompt = get_prompt(user_message, conversation_history)
    
    # Gemini APIに送信するチャット履歴を作成
    chat = model.start_chat(history=[
        {"role": "user" if item['role'] == 'human' else "model", "parts": [item['content']]}
        for item in conversation_history
    ])
    response = chat.send_message(full_prompt)
    
    # 会話履歴を更新
    conversation_history.append({
        'role': 'human',
        'content': user_message
    })
    conversation_history.append({
        'role': 'assistant',
        'content': response.text
    })
    session['conversation_history'] = conversation_history
    
    return jsonify({'response': response.text})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)