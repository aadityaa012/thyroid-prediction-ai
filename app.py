
from flask import Flask, request, redirect, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
import joblib

app = Flask(__name__)
app.secret_key = "change-this-to-a-long-random-secret"

model = joblib.load("model.pkl")
DB = "users.db"


def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)


init_db()

STYLE = """
<style>
* { box-sizing:border-box; }
body {
    margin:0; padding:25px; min-height:100vh;
    background:#07111f; color:#e8f2ff;
    font-family:Arial,sans-serif;
    display:flex; justify-content:center; align-items:center;
}
.card {
    width:100%; max-width:440px; padding:30px;
    background:#101e30; border:1px solid #29425c;
    border-radius:18px;
}
h1 { color:#42e8f5; }
p { color:#9aadc2; line-height:1.6; }
input {
    width:100%; padding:13px; margin:9px 0 16px;
    background:#091524; border:1px solid #29425c;
    border-radius:8px; color:white;
}
button {
    width:100%; padding:14px; border:0;
    border-radius:8px; background:#42e8f5;
    color:#07111f; font-weight:bold; cursor:pointer;
}
a { color:#42e8f5; }
.result {
    margin-top:20px; padding:18px;
    border:1px solid #1b7886; border-radius:10px;
    background:#0a2935; overflow-wrap:anywhere;
}
label { color:#d7e6f8; }
</style>
"""

LOGIN = """
<!DOCTYPE html><html><head><title>ThyroAI Login</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
""" + STYLE + """</head><body><div class="card">
<h1>✦ ThyroAI</h1>
<p>Sign in to your thyroid prediction dashboard.</p>
<form method="post">
<label>Username</label>
<input name="username" required autocomplete="username">
<label>Password</label>
<input type="password" name="password" required
autocomplete="current-password">
<button>Login</button>
</form>
<p>New user? <a href="/register">Create account</a></p>
{% if error %}<p>{{ error }}</p>{% endif %}
</div></body></html>
"""

REGISTER = """
<!DOCTYPE html><html><head><title>ThyroAI Register</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
""" + STYLE + """</head><body><div class="card">
<h1>Create Account</h1>
<p>Register to access ThyroAI.</p>
<form method="post">
<label>Username</label>
<input name="username" required minlength="3" maxlength="40"
autocomplete="username">
<label>Password (minimum 8 characters)</label>
<input type="password" name="password" required minlength="8"
autocomplete="new-password">
<button>Register</button>
</form>
<p>Already registered? <a href="/login">Login</a></p>
{% if error %}<p>{{ error }}</p>{% endif %}
</div></body></html>
"""

DASHBOARD = """
<!DOCTYPE html><html><head><title>ThyroAI Dashboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
""" + STYLE + """</head><body><div class="card" style="max-width:600px">
<p>THYROAI / PREDICTION DASHBOARD</p>
<h1>Welcome, {{ username }}!</h1>
<p>Enter the four features used by your trained model.</p>
<form method="post">
<label>Age</label>
<input type="number" name="age" min="1" max="120"
step="1" required>
<label>TSH</label>
<input type="number" name="tsh" min="0" step="any" required>
<label>T3</label>
<input type="number" name="t3" min="0" step="any" required>
<label>T4</label>
<input type="number" name="t4" min="0" step="any" required>
<button>Predict Thyroid Class</button>
</form>
{% if result is not none %}
<div class="result">
<p>MODEL PREDICTION</p><h2>{{ result }}</h2>
<p>This is an experimental model output, not a medical diagnosis.</p>
</div>
{% endif %}
{% if error %}<p>{{ error }}</p>{% endif %}
<p><a href="/logout">Logout</a></p>
</div></body></html>
"""


@app.route("/")
def home():
    if "username" not in session:
        return redirect("/login")
    return redirect("/dashboard")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if len(username) < 3:
            error = "Username must have at least 3 characters."
        elif len(password) < 8:
            error = "Password must have at least 8 characters."
        else:
            try:
                with sqlite3.connect(DB) as con:
                    con.execute(
                        "INSERT INTO users (username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password))
                    )
                return redirect("/login")
            except sqlite3.IntegrityError:
                error = "Username already exists. Choose another."

    return render_template_string(REGISTER, error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        with sqlite3.connect(DB) as con:
            user = con.execute(
                "SELECT username, password FROM users WHERE username = ?",
                (username,)
            ).fetchone()

        if user and check_password_hash(user[1], password):
            session.clear()
            session["username"] = user[0]
            return redirect("/dashboard")

        error = "Invalid username or password."

    return render_template_string(LOGIN, error=error)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "username" not in session:
        return redirect("/login")

    result = None
    error = None

    if request.method == "POST":
        try:
            age = float(request.form["age"])
            tsh = float(request.form["tsh"])
            t3 = float(request.form["t3"])
            t4 = float(request.form["t4"])

            if not 1 <= age <= 120:
                raise ValueError("Age must be between 1 and 120.")

            if min(tsh, t3, t4) < 0:
                raise ValueError("Lab values cannot be negative.")

            data = pd.DataFrame(
                [[age, tsh, t3, t4]],
                columns=["age", "tsh", "t3", "t4"]
            )

            result = str(model.predict(data)[0])

        except ValueError as e:
            error = str(e)
        except Exception:
            error = "Prediction failed. Check the model and input values."

    return render_template_string(
        DASHBOARD,
        username=session["username"],
        result=result,
        error=error
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)


