from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
import secrets
import subprocess

app = Flask(__name__)
app.secret_key = "secret123"


# -------------------------
# MODE TOGGLE
# -------------------------
@app.route("/toggle_mode")
def toggle_mode():
    if "user" not in session:
        return redirect("/")

    current_mode = session.get("mode", "vulnerable")

    if current_mode == "vulnerable":
        session["mode"] = "secure"
    else:
        session["mode"] = "vulnerable"

    return redirect("/dashboard")


# -------------------------
# LOGIN (SQL Injection)
# -------------------------
@app.route("/", methods=["GET", "POST"])
def login():

    # ✅ Set default ONLY first time (do NOT reset every time)
    if request.method == "GET":
        if "mode" not in session:
            session["mode"] = "vulnerable"

    mode = session.get("mode", "vulnerable")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # 🔴 Vulnerable Mode
        if mode == "vulnerable":
            query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
            user = c.execute(query).fetchone()

        # 🟢 Secure Mode
        else:
            query = "SELECT * FROM users WHERE username = ? AND password = ?"
            user = c.execute(query, (username, password)).fetchone()

        conn.close()

        if user:
            session["user"] = username

            if mode == "secure":
                session["csrf_token"] = secrets.token_hex(16)

            return redirect("/dashboard")
        else:
            return render_template("login.html", mode=mode, error="Invalid credentials")

    return render_template("login.html", mode=mode)

# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    mode = session.get("mode", "vulnerable")
    return render_template("dashboard.html", user=session["user"], mode=mode)


# -------------------------
# PROFILE (XSS + IDOR)
# -------------------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect("/")

    mode = session.get("mode", "vulnerable")
    user_id = request.args.get("id", "1")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        bio = request.form["bio"]
        c.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))
        conn.commit()

    if mode == "secure":
        # 🟢 Only own profile
        user = c.execute(
            "SELECT * FROM users WHERE username = ?",
            (session["user"],)
        ).fetchone()
    else:
        # 🔴 IDOR
        user = c.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()

    conn.close()

    return render_template("profile.html", user=user, mode=mode)


# -------------------------
# TRANSFER (CSRF)
# -------------------------
@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    if "user" not in session:
        return redirect("/")

    mode = session.get("mode", "vulnerable")
    message = ""

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # ✅ Fetch all users except current
    users = c.execute(
        "SELECT username FROM users WHERE username != ?",
        (session["user"],)
    ).fetchall()

    if request.method == "POST":

        # 🟢 CSRF protection (only in secure mode)
        if mode == "secure":
            token = request.form.get("csrf_token")
            if token != session.get("csrf_token"):
                return "CSRF Attack Detected!"

        to_user = request.form["to"]
        amount = request.form["amount"]

        message = f"Transferred ₹{amount} to {to_user}"

    conn.close()

    return render_template("transfer.html", message=message, mode=mode, users=users)

# -------------------------
# ADMIN (Access Control)
# -------------------------
@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/")

    mode = session.get("mode", "vulnerable")

    if mode == "secure" and session["user"] != "admin":
        return "Access Denied!"

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    users = c.execute("SELECT id, username FROM users").fetchall()

    conn.close()

    return render_template("admin.html", users=users, mode=mode)


# -------------------------
# PING (Command Injection)
# -------------------------
@app.route("/ping", methods=["GET", "POST"])
def ping():
    if "user" not in session:
        return redirect("/")

    mode = session.get("mode", "vulnerable")
    output = ""

    if request.method == "POST":
        ip = request.form["ip"]

        if mode == "vulnerable":
            # 🔴 unsafe
            command = f"ping -n 2 {ip}"
            output = os.popen(command).read()
        else:
            # 🟢 secure
            try:
                result = subprocess.run(
                    ["ping", "-n", "2", ip],
                    capture_output=True,
                    text=True
                )
                output = result.stdout
            except:
                output = "Invalid input!"

    return render_template("ping.html", output=output, mode=mode)


# -------------------------
# CONFIG (Misconfiguration)
# -------------------------
@app.route("/config")
def config():
    if "user" not in session:
        return redirect("/")

    mode = session.get("mode", "vulnerable")

    if mode == "vulnerable":
        config_data = {
            "DEBUG": True,
            "SECRET_KEY": app.secret_key,
            "DATABASE": "database.db",
            "PATH": "C:/Users/anjal/Downloads/OWASP-Lab"
        }
    else:
        config_data = {
            "DEBUG": False,
            "INFO": "Configuration hidden"
        }

    return render_template("config.html", config=config_data, mode=mode)

# -------------------------
# SECURITY CENTER
# -------------------------
@app.route("/security-center")
def security_center():

    if "user" not in session:
        return redirect("/")

    mode = session.get("mode", "vulnerable")

    return render_template(
        "security_center.html",
        mode=mode,
        user=session["user"]
    )

# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("csrf_token", None)   # 🔥 remove token too
    return redirect("/")

# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)



    