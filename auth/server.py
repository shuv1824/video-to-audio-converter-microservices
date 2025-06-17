import jwt, datetime, os
import sqlite3
from flask import Flask, g, request, jsonify

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect("auth.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db_connection()
    with app.open_resource("schema.sql", mode="r") as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


@app.route("/login", methods=["POST"])
def login():
    auth = request.authorization
    if not auth:
        return "Missing credentials", 401

    db = get_db_connection()

    user = db.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (auth.username, auth.password),
    ).fetchone()

    db.close()

    if user is None:
        return "Invalid credentials", 401

    token = jwt.encode(
        {
            "user": user["username"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
        },
        app.config["SECRET_KEY"],
    )

    return jsonify({"token": token})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
