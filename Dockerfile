# 基本イメージとしてPythonの公式イメージを使用
FROM python:3.11

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt ./
COPY gemini_web_app.py .
COPY prompts.py .
COPY templates/ ./templates/

# 必要なPythonライブラリをインストール
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 環境変数の設定
ENV FLASK_APP=gemini_web_app.py
ENV FLASK_ENV=development

# ポート5000を開放
EXPOSE 5000

# Flaskアプリケーションを実行
CMD ["flask", "run", "--host=0.0.0.0"]
