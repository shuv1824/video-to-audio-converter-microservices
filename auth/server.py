import jwt, datetime, os
from flask import Flask, g, request
import psycopg2

server = Flask(__name__)

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST"),
    "port": os.environ.get("DB_PORT"),
}


def get_db_connection():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = psycopg2.connect(**DB_CONFIG)
    return db


@server.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db_connection()
    with server.open_resource("schema.sql", mode="r") as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


@server.route("/login", methods=["POST"])
def login():
    auth = request.authorization
    if not auth:
        return "Missing credentials", 401

    db = get_db_connection()

    user = db.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (auth.username, auth.password),
    ).fetchone()

    db.close()

    if user is None:
        return "Invalid credentials", 401

    return create_jwt(auth.username, os.environ.get("JWT_SECRET"), True)


@server.route("/validate", methods=["POST"])
def validate():
    encoded_jwt = request.headers["Authorization"]
    if not encoded_jwt:
        return "Missing credentials", 401

    encoded_jwt = encoded_jwt.split(" ")[1]

    try:
        decoded = jwt.decode(
            encoded_jwt, os.environ.get("JWT_SECRET"), algorithms=["HS256"]
        )
    except:
        return "Not authorized", 403

    return decoded, 200


def create_jwt(username, secret, authz):
    return jwt.encode(
        {
            "username": username,
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=1),
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "authz": authz,
        },
        secret,
        algorithm="HS256",
    )


if __name__ == "__main__":
    init_db()
    server.run(host="0.0.0.0", port=5000)
