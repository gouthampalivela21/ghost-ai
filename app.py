import requests
import os
import json
from functools import wraps
from random import randint
from datetime import datetime
import secrets
import smtplib

import firebase_admin
from firebase_admin import credentials, firestore

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify,
    Response,
    abort,
    send_file,
)
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

from email.mime.text import MIMEText
from groq import Groq

from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
import wikipedia
import feedparser

from duckduckgo_search import DDGS
import traceback

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "email" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

from utils.sessions import register_session
FACT_RESOLVER=[]
def resolve_ipl_facts(text: str) -> str | None:
    t = text.lower()

    IPL_ORANGE_CAP = {
        2023: "Shubman Gill",
        2022: "Jos Buttler",
        2021: "Ruturaj Gaikwad",
        2020: "KL Rahul",
        2019: "David Warner",
        2018: "Kane Williamson",
    }

    if "orange cap" in t:
        for year, winner in IPL_ORANGE_CAP.items():
            if str(year) in t:
                return f"The {year} IPL Orange Cap winner was {winner}."

        return "I don’t have verified information for that year."

    return None

FACT_RESOLVER.append(resolve_ipl_facts)

def resolve_indian_leaders(text: str) -> str | None:
    t = text.lower()

    if "prime minister of india" in t:
        return "The current Prime Minister of India is Narendra Modi."

    if "president of india" in t:
        return "The current President of India is Droupadi Murmu."

    return None

FACT_RESOLVER.append(resolve_indian_leaders)

def is_fact_query(text: str) -> bool:
    keywords = [
        "who", "winner", "when", "year", "born",
        "orange cap", "ipl", "score", "record",
        "president", "prime minister"
    ]
    return any(k in text.lower() for k in keywords)

def get_verified_context(user_text: str) -> str:
    if is_fact_query(user_text):
        try:
            return wikipedia.summary(user_text, sentences=4)
        except:
            return ""
    return ""

def hallucination_guard(user_text: str, verified_context: str) -> str:
    return f"""
You are a factual assistant.

Rules:
- If you are NOT 100% sure of a fact, say "I don’t have verified information".
- Do NOT guess years, names, statistics.
- Do NOT mix multiple years.
- Use ONLY verified context if provided.

Verified context:
{verified_context}
"""

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
load_dotenv()

FLASK_SECRET = os.getenv("FLASK_SECRET")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SERVICE_ACCOUNT = os.getenv("SERVICE_ACCOUNT")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

ADMIN_EMAILS = {"youradmin@gmail.com"}  # change this

if not firebase_admin._apps:
   SERVICE_ACCOUNT_PATH = os.path.abspath(SERVICE_ACCOUNT) if SERVICE_ACCOUNT else None

if not firebase_admin._apps:
    if not SERVICE_ACCOUNT_PATH or not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise RuntimeError(
            "SERVICE_ACCOUNT path is invalid. "
            "Set full path in .env (e.g. /Users/you/project/serviceAccountKey.json)"
        )

    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()
users_col = db.collection("users")
messages_col = db.collection("messages")
api_keys_col = db.collection("api_keys")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = FLASK_SECRET
bcrypt = Bcrypt(app)

otp_storage = {}  # memory OTP

def needs_wikipedia(text: str) -> bool:
    keywords = [
        "who is", "what is", "explain", "define",
        "history", "about", "meaning"
    ]
    t = text.lower()
    return any(k in t for k in keywords)

def wikipedia_lookup(query: str) -> str:
    try:
        wikipedia.set_lang("en")
        return wikipedia.summary(query, sentences=5, auto_suggest=True)
    except wikipedia.DisambiguationError as e:
        try:
            return wikipedia.summary(e.options[0], sentences=4)
        except Exception:
            return ""
    except Exception:
        return ""



def needs_news(text: str) -> bool:
    keywords = [
        "news", "latest", "today", "current",
        "update", "updates", "breaking",
        "price", "launch", "released"
    ]
    t = text.lower()
    return any(k in t for k in keywords)


def google_news_lookup(query: str) -> str:
    try:
        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        )

        feed = feedparser.parse(rss_url)

        summaries = []
        for entry in feed.entries[:5]:
            summaries.append(
                f"- {entry.title} ({entry.published})\n  {entry.link}"
            )

        return "\n".join(summaries)

    except Exception:
        return ""

def needs_search(text: str) -> bool:
    keywords = [
        "how to", "best", "compare", "vs",
        "tool", "library", "framework",
        "alternative", "example", "tutorial",
        "use case", "guide"
    ]
    t = text.lower()
    return any(k in t for k in keywords)


def duckduckgo_lookup(query: str) -> str:
    try:
        results = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                title = r.get("title", "")
                snippet = r.get("body", "")
                link = r.get("href", "")
                if title and snippet:
                    results.append(f"- {title}\n  {snippet}")

        return "\n".join(results)

    except Exception:
        return ""

def inject_wikipedia_context(user_text: str) -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    context_blocks = []

    if needs_news(user_text):
        news_text = google_news_lookup(user_text)
        if news_text:
            context_blocks.append(
                f"GOOGLE NEWS (retrieved {today}):\n{news_text}"
            )

    if needs_wikipedia(user_text):
        wiki_text = wikipedia_lookup(user_text)
        if wiki_text:
            context_blocks.append(
                f"WIKIPEDIA (retrieved {today}):\n{wiki_text}"
            )

    if not context_blocks and needs_search(user_text):
        search_text = duckduckgo_lookup(user_text)
        if search_text:
            context_blocks.append(
                f"WEB SEARCH (DuckDuckGo, retrieved {today}):\n{search_text}"
            )

    if not context_blocks:
        return user_text

    combined_context = "\n\n".join(context_blocks)

    return f"""
SYSTEM NOTE:
Today's date: {today}

LIVE INFORMATION:
{combined_context}

IMPORTANT:
- Prefer LIVE INFORMATION when answering
- Cite uncertainty if data is incomplete

USER QUESTION:
{user_text}
"""

def send_otp(email: str) -> bool:
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("Missing email credentials")
        return False

    otp = randint(100000, 999999)
    otp_storage[email] = otp

    msg = MIMEText(
        f"""
        <html>
    <body style="font-family: Arial, sans-serif; background: #0d0d0d; color: #fff; padding: 20px;">
        <div style="max-width: 480px; margin: auto; background: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #333;">
        <h2 style="text-align:center; color:#8B5CF6;">GHost AI Verification Code</h2>

        <p style="font-size: 16px;">
            Hi there, 👋<br><br>
            It looks like you are trying to change your password. This your OTP for <b>GHost AI</b>.
        </p>

        <p style="font-size: 18px; font-weight: bold; text-align:center; padding: 14px; background: #2e2e2e; border-radius: 8px; letter-spacing:2px; color:#8B5CF6;">
            {otp}
        </p>

        <p style="font-size: 14px; color:#ccc;">
            ❗️ This code will expire shortly.<br>
            ❌ Do not share this code with anyone.
        </p>

        <hr style="border:0; border-top:1px solid #333; margin: 20px 0;">

        <p style="text-align:center; font-size:12px; color:#666;">
            Sent by <b>GHost AI</b><br>
            If you did not request this, you can safely ignore this email.
        </p>
        </div>
    </body>
    </html>
    """,
        "html",
    )

    msg["Subject"] = "GHost AI - OTP Verification"
    msg["From"] = f"GHost AI 👻 <{EMAIL_ADDRESS}>"
    msg["To"] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        return True
    except Exception as e:
        print("OTP error:", e)
        return False


def send_password_changed_email(email: str):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("Missing email credentials")
        return False

    msg = MIMEText(
        """
    <html>
      <body style="font-family: Arial, sans-serif; background: #0d0d0d; color: #fff; padding: 20px;">
        <div style="max-width: 480px; margin: auto; background: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #333;">
          <h2 style="text-align:center; color:#8B5CF6;">GHost AI Password Updated</h2>

          <p style="font-size: 16px;">
            Hello, 👋<br><br>
            This is to let you know that your password has been successfully updated for your <b>GHost AI 👻</b> account.
          </p>

          <p style="font-size: 14px; color:#ccc;">
            If you made this change, no action is required.<br>
            If you did <b>not</b> change your password, please reset it immediately.
          </p>

          <hr style="border:0; border-top:1px solid #333; margin: 20px 0;">

          <p style="text-align:center; font-size:12px; color:#666;">
            Sent by <b>GHost AI 👻</b><br>
            Keep your account secure.
          </p>
        </div>
      </body>
    </html>
    """,
        "html",
    )

    msg["Subject"] = "GHost AI - Password Changed"
    msg["From"] = f"GHost AI 👻 "
    msg["To"] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        return True
    except Exception as e:
        print("Password change email error:", e)
        return False

@app.route("/")
def index():
    if session.get("email"):
        return redirect("/chat")
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")

        if not name or not email or not pw:
            return render_template("signup.html", error="Please fill in all fields")

        if users_col.document(email).get().exists:
            return render_template("signup.html", error="Email already exists")

        hashed = bcrypt.generate_password_hash(pw).decode("utf-8")
        users_col.document(email).set(
            {
                "name": name,
                "email": email,
                "password": hashed,
                "photo": "https://i.pravatar.cc/150?u=" + email,
                "verified": False,
            }
        )

        session["verify_email"] = email
        send_otp(email)
        return redirect("/verify")

    return render_template("signup.html")

@app.route("/intro")
def intro():
    return render_template("intro.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/premium")
def premium():
    return render_template("premium.html")

@app.route("/connect")
def connect():
    return render_template("connect.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")

        if not email or not pw:
            return render_template("login.html", error="Please enter email & password")

        doc = users_col.document(email).get()
        if not doc.exists:
            return render_template("login.html", error="User not found")

        user = doc.to_dict()
        if not bcrypt.check_password_hash(user["password"], pw):
            return render_template("login.html", error="Incorrect password")

        session["email"] = email
        session["name"] = user.get("name")
        session["photo"] = user.get("photo")

        register_session(db, email, request)

        return redirect("/chat")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        doc = users_col.document(email).get()
        if not doc.exists:
            return render_template("forgot_password.html", error="Email not found")

        send_otp(email)
        session["reset_email"] = email
        return redirect("/reset-password")

    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")
    if not email:
        return redirect("/forgot-password")

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        new_pw = request.form.get("password", "").strip()

        if not otp or not new_pw:
            return render_template(
                "reset_password.html", error="Please fill all fields"
            )

        if str(otp_storage.get(email)) != otp:
            return render_template("reset_password.html", error="Incorrect OTP")

        hashed = bcrypt.generate_password_hash(new_pw).decode("utf-8")
        users_col.document(email).update({"password": hashed})

        send_password_changed_email(email)

        otp_storage.pop(email, None)
        session.pop("reset_email", None)

        return redirect("/login")

    return render_template("reset_password.html")


os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # dev only

GOOGLE_REDIRECT_URI = "http://127.0.0.1:5000/login/callback"

flow = Flow.from_client_secrets_file(
    "client_secret.json",
    scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_uri=GOOGLE_REDIRECT_URI,
)

@app.route("/login/google")
def login_google():
    authorization_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true"
    )
    session["oauth_state"] = state
    return redirect(authorization_url)

@app.route("/connect/google")
def connect_google():
    authorization_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true"
    )
    session["oauth_state"] = state
    session["oauth_action"] = "connect"   # 👈 important
    return redirect(authorization_url)

@app.route("/login/callback")
def login_callback():
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = google.auth.transport.requests.Request()

    id_info = id_token.verify_oauth2_token(
        credentials._id_token,
        request_session,
        GOOGLE_CLIENT_ID
    )

    email = id_info.get("email")
    name = id_info.get("name")
    photo = id_info.get("picture")

    if session.get("oauth_action") == "connect":
        
        users_col.document(session["email"]).update({
            "photo": photo,
            "name": name
        })

        session["name"] = name
        session["photo"] = photo
        session["oauth_action"] = None

        return redirect("/settings")   

    doc = users_col.document(email).get()

    if not doc.exists:
        users_col.document(email).set({
            "name": name,
            "email": email,
            "photo": photo,
            "verified": True
        })

    session["email"] = email
    session["name"] = name
    session["photo"] = photo

    register_session(db, email, request)

    return redirect("/chat")

@app.route("/chat")
def chat():
    if "email" not in session:
        return redirect("/login")

    cfg = os.getenv("FIREBASE_CLIENT_CONFIG")
    return render_template("chat.html", firebase_config_json=cfg)


@app.route("/api/history")
def api_history():
    email = session.get("email")
    if not email:
        return jsonify([]), 401

    docs = (
    db.collection("messages")
    .where("user", "==", email)
    .order_by("ts", direction=firestore.Query.DESCENDING)
    .limit(20)
    .stream()
)

    out = []
    for d in docs:
        x = d.to_dict()
        out.append(
            {
                "sender": x.get("sender"),
                "text": x.get("text"),
                "convo": x.get("convo", "default"),
            }
        )
    return jsonify(out)


def groq_stream(text: str, full_reply_holder: list):
    if not groq_client:
        print("Groq client not configured")
        return

    verified_context = get_verified_context(text)
    guard_prompt = hallucination_guard(text, verified_context)

    messages = [
        {"role": "system", "content": guard_prompt},
        {"role": "user", "content": text},
    ]

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            stream=True,
        )

        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_reply_holder[0] += delta.content
                yield delta.content   

    except Exception as e:
        print("Groq stream error:", e)
        return
    
@app.route("/stream", methods=["POST"])
def stream_reply():
    email = session.get("email")
    if not email:
        return "Unauthorized", 401

    body = request.json or {}
    text = body.get("message", "")
    convo = body.get("convo", "default")

    final_text =text

    messages_col.add({
        "user": email,
        "sender": "user",
        "text": text,              
        "convo": convo,
        "ts": datetime.utcnow(),
    })

    def generate():
        full_reply = [""]

        try:
            for chunk in groq_stream(final_text, full_reply):  
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            err = "⚠️ AI backend error"
            yield f"data: {json.dumps({'chunk': err})}\n\n"
            return

        messages_col.add({
            "user": email,
            "sender": "bot",
            "text": full_reply[0],
            "convo": convo,
            "ts": datetime.utcnow(),
        })

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True)