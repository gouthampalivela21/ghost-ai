# auth_routes.py

from flask import request, session, redirect
from utils.sessions import register_session

@app.route("/login", methods=["POST"])
def login():
    user = authenticate_user()
    if not user:
        return "Invalid credentials", 401

    # ✅ register session ONLY here
    register_session(user, request)

    session["user_id"] = str(user["_id"])
    return redirect("/chat")