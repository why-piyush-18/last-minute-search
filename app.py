import os
from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------ Flask Setup ------------------
app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Direct secret key

DB_NAME = "database.db"

# ------------------ Gemini API Setup (Direct Key) ------------------
GEMINI_API_KEY = "AIzaSyCHZldaOYWq5_8W6lQ1aQ0JvfN73az82no"  # <-- Put your real key here

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not set! Chatbot won't work until you set it.")
else:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")  # Replace with correct model

# ------------------ Database ------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_NAME)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db:
        db.close()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()

with app.app_context():
    init_db()

# ------------------ Authentication ------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        cursor = get_db().cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session["user"] = username
            return redirect(url_for("chat"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

# Signup Page Route (GET)
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        username = request.form.get("username")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Password match check
        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match")

        hashed_password = generate_password_hash(password)

        try:
            cursor = get_db().cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            get_db().commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="Username already exists")

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ------------------ Chat Routes ------------------
@app.route("/chat")
def chat():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", username=session["user"])

@app.route("/get_response", methods=["POST"])
def get_response():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not set"}), 500

    try:
        user_message = request.json.get("message")
        if not user_message:
            return jsonify({"error": "No message"}), 400

        # Gemini API call
        response = model.generate_content(user_message)
        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ Run Flask ------------------
if __name__ == "__main__":
    app.run(debug=True)
