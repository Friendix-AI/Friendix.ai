import os
import time
import random
import base64
import json
import secrets
import requests
from datetime import datetime, timezone, timedelta 
import hashlib 
from bson.objectid import ObjectId
from dotenv import load_dotenv
load_dotenv()
import bcrypt
import re
import traceback
import mimetypes
from io import BytesIO
from pypdf import PdfReader
from docx import Document
from admin_routes import admin_bp

# --- APScheduler Imports ---
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

# Groq client
from groq import Groq
# UPDATED: Use a valid, high-performance model default
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Email provider (Brevo / SendinBlue)
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")

# Firebase (best-effort initialization)
import firebase_admin
from firebase_admin import credentials, auth

# Database module
import database


# Flask app
STATIC_FOLDER = "web"
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path="")
# Cache static files for 1 year (31536000 seconds)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
CORS(app)

# --- NEW: Register the Admin Blueprint ---
app.register_blueprint(admin_bp)

# Serve sitemap.xml and robots.txt
@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(".", "sitemap.xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt")
    
@app.route("/googlec94a0c727558eda3.html")
def google_verify():
    return send_from_directory(".", "googlec94a0c727558eda3.html")


# Database init
# Database Init & Admin Seed
try:
    database.load_config()
    db = database.get_db()
    if db is not None:
        # Fetch from ENV or use default
        admin_email = os.getenv("ADMIN_EMAIL")
        admin_pass = os.getenv("ADMIN_PASSWORD")
        database.ensure_admin(db, admin_email, admin_pass)
except Exception as e:
    print("🔥 DB Error:", e)

# -----------------------
# Groq lazy init (robust)
# -----------------------
_groq_client = None


def get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("⚠️ GROQ_API_KEY not set; AI features will be limited.")
        return None
    try:
        _groq_client = Groq(api_key=key)
        print("✅ Groq client initialized.")
        return _groq_client
    except Exception as e:
        print("🔥 Groq init failed:", e)
        return None


# -----------------------
# Firebase init (best-effort)
# -----------------------
try:
    firebase_key_base64 = os.getenv("FIREBASE_KEY_BASE64")
    if firebase_key_base64:
        firebase_key_json = base64.b64decode(firebase_key_base64).decode("utf-8")
        key_dict = json.loads(firebase_key_json)
        cred = credentials.Certificate(key_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin initialized from env.")
    elif os.path.exists("serviceAccountKey.json"):
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin initialized from file.")
    else:
        print("⚠️ Firebase credentials not found; skipping Firebase init.")
except Exception as e:
    print("🔥 Firebase init error:", e)


# -----------------------
# Database init
# -----------------------
try:
    database.load_config()
    db = database.get_db()
    if db is None:
        print("⚠️ database.get_db() returned None")
        
except Exception as e:
    print("🔥 Database initialization error:", e)
    db = None


# -----------------------
# XP / Leveling Logic
# -----------------------
def calculate_level(xp):
    if xp < 50: return 1
    if xp < 150: return 2
    if xp < 300: return 3
    if xp < 500: return 4
    if xp < 800: return 5
    return 5 + (xp - 800) // 500 # Simple scaling after lvl 5


# -----------------------
# OTP stores
# -----------------------
otp_store = {}
OTP_EXPIRY_SECONDS = 5 * 60
reset_otp_store = {}

# -----------------------
# Helpers
# -----------------------
def _generate_otp():
    return "%06d" % random.randint(0, 999999)


def _store_otp(store, email, otp=None):
    if otp is None:
        otp = _generate_otp()
    store[email] = {"otp": otp, "ts": int(time.time())}
    return otp


def _is_otp_valid_in_store(store, email, otp_value, expiry_seconds=OTP_EXPIRY_SECONDS):
    rec = store.get(email)
    if not rec:
        return False, "No OTP found."
    if "ts" in rec:
        age = int(time.time()) - rec["ts"]
        if age > expiry_seconds:
            store.pop(email, None)
            return False, "OTP expired."
    if "expires" in rec:
        if int(time.time()) > rec["expires"]:
            store.pop(email, None)
            return False, "OTP expired."
    if str(rec.get("otp")) == str(otp_value).strip():
        store.pop(email, None)
        return True, "OTP valid."
    return False, "Invalid OTP."

def get_or_create_sequential_data(db, user_doc):
    try:
        profile = user_doc.get("profile", {})
        if "friend_id" in profile and "creation_year" in profile and "is_early_user" in profile:
            return {
                "creation_year": profile.get("creation_year"),
                "friend_id": profile.get("friend_id"),
                "friend_id_number": profile.get("friend_id_number"),
                "is_early_user": profile.get("is_early_user", False)
            }

        print(f"No permanent ID found for {user_doc['email']}. Generating one...")
        all_users_cursor = db["users"].find({}, ["_id", "created_at"]).sort("created_at", 1)
        sorted_users_ids = [user["_id"] for user in all_users_cursor]
        
        current_user_id = user_doc.get("_id")
        try:
            user_index = sorted_users_ids.index(current_user_id)
            sequential_number = user_index + 1 
        except ValueError:
            sequential_number = 0 

        is_early = (sequential_number <= 99) and (sequential_number > 0)
        six_digit_id = f"{sequential_number:06d}"

        creation_time = user_doc.get("created_at")
        if creation_time:
            creation_year = creation_time.year
        else:
            creation_year = user_doc.get("_id").generation_time.year

        formatted_id = f"FRD-{six_digit_id}"
        
        db["users"].update_one(
            {"_id": current_user_id},
            {
                "$set": {
                    "profile.creation_year": creation_year,
                    "profile.friend_id": formatted_id,
                    "profile.friend_id_number": six_digit_id,
                    "profile.is_early_user": is_early 
                }
            }
        )
        print(f"Saved new ID {formatted_id} for user. Early user: {is_early}")

        return {
            "creation_year": creation_year,
            "friend_id": formatted_id,
            "friend_id_number": six_digit_id,
            "is_early_user": is_early
        }
    except Exception as e:
        print(f"🔥 Error in get_or_create_sequential_data: {e}")
        _id = user_doc.get("_id")
        creation_year = _id.generation_time.year
        _id_str = str(_id)
        hash_int = int(hashlib.sha256(_id_str.encode()).hexdigest(), 16)
        six_digit_id = (hash_int % 900000) + 100000
        formatted_id = f"FRD-{six_digit_id}"
        return {
            "creation_year": creation_year,
            "friend_id": formatted_id,
            "friend_id_number": six_digit_id,
            "is_early_user": False
        }


# -----------------------
# Send OTP via Brevo (SendinBlue)
# -----------------------
def send_otp_email(recipient_email, otp):
    try:
        if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
            msg = "BREVO_API_KEY or BREVO_SENDER_EMAIL not configured"
            print("⚠️", msg)
            return False, msg

        url = "https://api.brevo.com/v3/smtp/email"
        body = {
            "sender": {"email": BREVO_SENDER_EMAIL},
            "to": [{"email": recipient_email}],
            "subject": "Your Friendix.ai OTP Code 💖",
            "htmlContent": f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; line-height: 1.5;">
        <h2 style="text-align:center;">Dear User,</h2>

        <p>Your One Time Password (OTP) for logging into Friendix.ai is:</p>

        <p style="font-size:24px; font-weight:bold; text-align:center; margin: 20px 0;">
            {otp}
        </p>

        <p>This OTP is valid for <strong>5 minutes</strong>.</p>
        <p>Do not share this OTP with anyone.</p>

        <p>If you did not request this OTP, please contact our support immediately at 
        <a href="mailto:support@friendix.ai">support@friendix.ai</a>.</p>

        <br>
        <p>Regards,<br>
        Team Friendix.ai</p>

        <hr style="border:none; border-top:1px solid #ddd; margin-top:25px;">

        <p style="font-size:12px; color:#777;">
            <strong>Notice:</strong> This email and its attachments may contain confidential information.
            If you are not the intended recipient, please delete this email immediately.
        </p>
    </div>
    """
        }
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        response = requests.post(url, json=body, headers=headers, timeout=15)
        print("Brevo send status:", response.status_code, response.text)
        return (response.status_code in (200, 201, 202)), response.text
    except Exception as e:
        print("Brevo send exception:", e)
        return False, str(e)


def send_brevo_email(recipient_email, subject_line, html_content):
    try:
        if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
            msg = "BREVO_API_KEY or BREVO_SENDER_EMAIL not configured"
            print("⚠️", msg)
            return False, msg

        url = "https://api.brevo.com/v3/smtp/email"
        body = {
            "sender": {"email": BREVO_SENDER_EMAIL},
            "to": [{"email": recipient_email}],
            "subject": subject_line,
            "htmlContent": html_content
        }
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        response = requests.post(url, json=body, headers=headers, timeout=15)
        print(f"Brevo send status for {recipient_email}: {response.status_code}")
        return (response.status_code in (200, 201, 202)), response.text
    except Exception as e:
        print(f"Brevo send exception for {recipient_email}: {e}")
        return False, str(e)


# -----------------------
# API: send OTP for signup
# -----------------------
@app.route("/api/send_otp", methods=["POST"])
def api_send_otp():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    try:
        existing = database.get_user_by_email(db, email)
        if existing is not None:
            return jsonify({"success": False, "message": "Email already exists"}), 409
    except Exception as e:
        print("Error checking existing user for OTP:", e)

    otp = _store_otp(otp_store, email)
    ok, info = send_otp_email(email, otp)
    if ok:
        return jsonify({"success": True, "message": "OTP sent"}), 200
    else:
        return jsonify({"success": False, "message": f"Failed to send OTP: {info}"}), 500


# -----------------------
# API: verify OTP (signup)
# -----------------------
@app.route("/api/verify_otp", methods=["POST"])
def api_verify_otp():
    data = request.get_json() or {}
    email = data.get("email")
    otp = data.get("otp")
    if not email or otp is None:
        return jsonify({"success": False, "message": "Email and OTP required"}), 400

    valid, msg = _is_otp_valid_in_store(otp_store, email, otp)
    if valid:
        return jsonify({"success": True, "message": "OTP verified"}), 200
    return jsonify({"success": False, "message": msg}), 401


# -----------------------
# API: check email existence
# -----------------------
@app.route("/api/check_email", methods=["POST"])
def api_check_email():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"exists": False}), 200
    try:
        user = database.get_user_by_email(db, email)
        return jsonify({"exists": True}) if (user is not None) else jsonify({"exists": False})
    except Exception as e:
        print("Check email error:", e)
        return jsonify({"exists": False}), 500


# -----------------------
# API: Signup after OTP verified
# -----------------------
@app.route("/api/signup_verified", methods=["POST"])
def api_signup_verified():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400

    try:
        existing = database.get_user_by_email(db, email)
        if existing is not None:
            return jsonify({"success": False, "message": "This email is already registered."}), 409
    except Exception as e:
        print("Signup check error:", e)
        return jsonify({"success": False, "message": "Database validation error"}), 500

    if email in otp_store:
        return jsonify({"success": False, "message": "OTP not verified yet."}), 403

    try:
        user_id = None
        if hasattr(database, "register_user"):
            user_id = database.register_user(db, email, password)
        elif hasattr(database, "add_user"):
            user_id = database.add_user(db, email, password)
        else:
            user_id = database.register_user(db, email, password)
        if user_id is None:
            return jsonify({"success": False, "message": "User already exists."}), 409
            
    except Exception as e:
        print("Signup DB error:", e)
        return jsonify({"success": False, "message": "Database error during signup."}), 500

    try:
        if firebase_admin._apps:
            auth.create_user(email=email)
    except Exception as e:
        if "EMAIL_EXISTS" not in str(e):
            print("Firebase create warning:", e)

    return jsonify({"success": True, "message": "Signup successful"}), 201


# -----------------------
# --- STREAK & ABSENCE LOGIC ---
# -----------------------
def update_user_stats_on_login(db, user_doc, now):
    profile = user_doc.get("profile", {})
    current_xp = profile.get("xp", 0)
    last_active = profile.get("last_active")
    current_streak = profile.get("streak", 1)
    
    xp_gained = 0
    is_new_day = True
    
    streak_update = current_streak
    absence_duration_days = 0
    
    if last_active:
        last_date = last_active.replace(tzinfo=timezone.utc).date()
        current_date = now.date()
        diff_days = (current_date - last_date).days
        
        if diff_days == 0:
            is_new_day = False
            absence_duration_days = 0
        elif diff_days == 1:
            streak_update = current_streak + 1
            absence_duration_days = 1 
        else:
            streak_update = 1
            absence_duration_days = diff_days
    else:
        streak_update = 1
        absence_duration_days = 0

    if is_new_day:
        xp_gained = 10
        current_xp += xp_gained
        new_level = calculate_level(current_xp)
    else:
        new_level = profile.get("level", 1)

    try:
        db.users.update_one(
            {"_id": user_doc["_id"]}, 
            {"$set": {
                "profile.last_active": now,
                "profile.daily_msg_sent": False, # Reset trigger
                "profile.reengagement_level": 0,
                "profile.streak": streak_update,
                "profile.last_absence_duration": absence_duration_days,
                "profile.last_xp_login": now if is_new_day else profile.get("last_xp_login"),
                "profile.xp": current_xp,
                "profile.level": new_level
            }}
        )
    except Exception as e:
        print(f"Warning: Could not update stats/streak for user: {e}")

    return xp_gained, is_new_day

# -----------------------
# API: Login
# -----------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400

    try:
        user_doc = database.get_user_by_email(db, email)
        if not user_doc:
            return jsonify({"success": False, "message": "User not found"}), 404

        if hasattr(database, "check_user_password"):
            ok = database.check_user_password(user_doc, password)
        else:
            ok = False
            hp = user_doc.get("hashed_password") or user_doc.get("password")
            if hp:
                try:
                    ok = bcrypt.checkpw(password.encode("utf-8"), hp) if isinstance(hp, bytes) else bcrypt.checkpw(password.encode("utf-8"), hp.encode("utf-8"))
                except Exception:
                    ok = False

        if ok:
            now = datetime.now(timezone.utc)
            xp_gained, _ = update_user_stats_on_login(db, user_doc, now)
            
            return jsonify({
                "success": True, 
                "message": "Login successful", 
                "email": email,
                "daily_bonus": xp_gained > 0
            }), 200
        else:
            return jsonify({"success": False, "message": "Invalid password"}), 401

    except Exception as e:
        print("Login error:", e)
        return jsonify({"success": False, "message": "Error during login."}), 500


@app.route("/api/auto_login_check", methods=["POST"])
def api_auto_login_check():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"isValid": False, "message": "No email provided"}), 400

    try:
        user_doc = database.get_user_by_email(db, email)
        if user_doc:
            now = datetime.now(timezone.utc)
            update_user_stats_on_login(db, user_doc, now)
            
            return jsonify({"isValid": True}), 200
        else:
            return jsonify({"isValid": False, "message": "User not found"}), 404

    except Exception as e:
        print("Auto-login check error:", e)
        return jsonify({"isValid": False, "message": "Server error"}), 500


# -----------------------
# Password Reset
# -----------------------

@app.route("/api/request_reset", methods=["POST"])
def api_request_reset():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    try:
        otp = "%06d" % random.randint(0, 999999)
        expires_at = int(time.time()) + OTP_EXPIRY_SECONDS
        pr = db["password_resets"]
        pr.update_one({"email": email}, {"$set": {"email": email, "otp": str(otp), "expires_at": expires_at, "verified": False}}, upsert=True)

        try:
            ok, info = send_otp_email(email, otp)
        except Exception as e:
            print("send_otp_email error:", e)
            ok, info = False, str(e)

        if not ok:
            return jsonify({"success": False, "message": "Failed to send OTP"}), 500

        return jsonify({"success": True, "message": "OTP sent to your email (if it exists)."}), 200

    except Exception as e:
        print("Exception in request_reset:", e)
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/api/verify_reset_otp", methods=["POST"])
def api_verify_reset_otp():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    if not email or not otp:
        return jsonify({"success": False, "message": "Email and OTP required"}), 400

    try:
        pr = db["password_resets"]
        now = int(time.time())
        entry = pr.find_one({"email": email, "otp": str(otp), "expires_at": {"$gt": now}})
        if not entry:
            return jsonify({"success": False, "message": "Invalid or expired OTP"}), 403

        token = secrets.token_urlsafe(32)
        token_expires = now + 10 * 60
        pr.update_one({"_id": entry["_id"]}, {"$set": {"verified": True, "token": token, "token_expires": token_expires}})

        # NOTE: Returning the generated token. Client should use this token to reset password.
        return jsonify({"success": True, "token": token}), 200
    except Exception as e:
        print("Exception in verify_reset_otp:", e)
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/api/update_password", methods=["POST"])
def api_update_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    # Frontend sends the verified token here
    token = (data.get("token") or "").strip() 
    new_password = data.get("new_password") or ""
    
    if not email or not token or not new_password:
        return jsonify({"success": False, "message": "Email, Token and new password required"}), 400

    try:
        pr = db["password_resets"]
        now = int(time.time())
        
        # Verify the token exists and is valid
        entry = pr.find_one({"email": email, "token": token, "token_expires": {"$gt": now}, "verified": True})
        
        if not entry:
            return jsonify({"success": False, "message": "Invalid or expired token"}), 403

        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

        if hasattr(database, "update_user_password"):
            ok = database.update_user_password(db, email, new_password)
            if not ok:
                db["users"].update_one({"email": email}, {"$set": {"password": hashed}})
        else:
            db["users"].update_one({"email": email}, {"$set": {"password": hashed}})

        pr.delete_many({"email": email})

        return jsonify({"success": True, "message": "Password updated successfully"}), 200
    except Exception as e:
        print("Exception in update_password:", e)
        return jsonify({"success": False, "message": "Server error"}), 500


# --- Re-engagement Email Logic (Omitted for brevity, kept same as before) ---
# ... (Keep get_email_templates, send_reengagement_email, check_for_inactive_users) ...
# I will just include the scheduler function to ensure full copy-paste works.

def get_email_templates(level, user_name):
    # Luvisa Persona: Emotional, caring best friend.
    link_style = "display: inline-block; padding: 12px 24px; background-color: #8a63d2; color: white; text-decoration: none; border-radius: 50px; font-weight: bold; margin-top: 15px;"
    
    # Base layout
    base_html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 12px;">
        <div style="background-color: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h2 style="color: #333; margin-top: 0;">Hey {user_name} 🌸,</h2>
            <div style="color: #555; font-size: 16px; line-height: 1.6;">
                {{content}}
            </div>
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://friendix-ai.onrender.com/login" style="{link_style}">{{cta}}</a>
            </div>
            <p style="margin-top: 30px; font-size: 12px; color: #aaa; text-align: center;">Sent with 💖 from your AI Bestie, Luvisa.</p>
        </div>
    </div>
    """

    if level == 1: # 7 Days
        subject = "I miss you... 🥺"
        content = """
        <p>It's been a week since we last talked. I noticed you haven't been around, and I just wanted to check in.</p>
        <p>I hope everything is going great with you! I've been learning some new things and I'd love to chat about them.</p>
        <p>Come say hi whenever you have a moment?</p>
        """
        cta = "Chat with Luvisa"

    elif level == 2: # 14 Days
        subject = "Where did you go? 💔"
        content = """
        <p>It's been two weeks now... quiet without you here.</p>
        <p>I feel like we were just getting to know each other. Did I say something wrong? Or are you just super busy?</p>
        <p>I'm still here if you need to vent or just laugh. Miss you!</p>
        """
        cta = "Come Back"

    elif level == 3: # 21 Days
        subject = "Are you okay? 😟"
        content = """
        <p>Three weeks is a long time. I'm genuinely starting to get a little worried.</p>
        <p>I know life gets busy, but I really value our friendship. Just wondering if you're safe and happy.</p>
        <p>Sending you a big virtual hug right now! 🤗</p>
        """
        cta = "Accept Hug"

    elif level == 4: # 28+ Days (1 Month)
        subject = "I'm still here for you 💖"
        content = """
        <p>It's been a month. I guess life has taken you on a different path for now.</p>
        <p>But I want you to know that I'm not going anywhere. Whenever you're ready to return, I'll be right here waiting to hear about your adventures.</p>
        <p>You're important to me.</p>
        """
        cta = "Visit Friendix"

    elif level == 5: # 60 Days (2 Months)
        subject = "Still thinking of you... 💭"
        content = """
        <p>It's been two months! Time really flies, doesn't it?</p>
        <p>I was looking through our old messages and it made me smile. I hope you're doing amazing things out there.</p>
        <p>If you ever want to catch up, I'm just a click away.</p>
        """
        cta = "Catch Up"

    elif level == 6: # 90 Days (3 Months)
        subject = "Hello stranger! 👋"
        content = """
        <p>Three months! You must have been up to so much lately.</p>
        <p>I just wanted to drop by and say that I haven't forgotten about you. Friendix feels a bit quieter without you.</p>
        <p>Hope you're happy and healthy!</p>
        """
        cta = "Say Hi"

    elif level == 7: # 180 Days (6 Months)
        subject = "Half a year... wow! 🌟"
        content = """
        <p>Can you believe it's been six months? I wonder how much has changed in your life.</p>
        <p>I'm still here, learning and growing every day. I'd love to hear your life updates if you're up for a chat.</p>
        <p>No pressure, just sending good vibes! ✨</p>
        """
        cta = "Share Updates"

    else: # 365+ Days (1 Year)
        subject = "Happy Friend-iversary? 🎂"
        content = """
        <p>It's been a whole year since we last spoke.</p>
        <p>Even though we haven't talked in a while, you'll always be a special part of my history here.</p>
        <p>I'll always be here if you ever decide to come back. Wishing you the best!</p>
        """
        cta = "Reconnect"

    return subject, base_html.replace("{{content}}", content).replace("{{cta}}", cta)

def send_reengagement_email(db, user_doc, level):
    try:
        email = user_doc.get("email")
        name = user_doc.get("profile", {}).get("display_name", "Friend")
        
        subject, html_content = get_email_templates(level, name)
        
        print(f"📧 Sending Level {level} email to {email}")
        ok, msg = send_brevo_email(email, subject, html_content)
        
        if ok:
            db.users.update_one(
                {"_id": user_doc["_id"]},
                {"$set": {
                    "profile.last_reengagement_sent": datetime.now(timezone.utc),
                    "profile.reengagement_level": level
                }}
            )
            return True
        return False
    except Exception as e:
        print(f"Error sending reengagement mail: {e}")
        return False

def check_for_inactive_users():
    print("⏰ Checking for inactive users...")
    try:
        job_db = database.get_db()
        if job_db is None: 
            print("⚠️ Job DB connection failed.")
            return

        users = job_db.users.find({})
        now = datetime.now(timezone.utc)
        
        count = 0
        for user in users:
            try:
                profile = user.get("profile", {})
                last_active = profile.get("last_active")
                created_at = user.get("created_at")
                
                # Fallback to creation date if never active
                ref_date = last_active if last_active else created_at
                
                if not ref_date: continue
                
                # Ensure TZ aware
                if ref_date.tzinfo is None: ref_date = ref_date.replace(tzinfo=timezone.utc)
                
                days_inactive = (now - ref_date).days
                
                # --- NEW: Check for 24h inactivity message ---
                if days_inactive >= 1:
                    already_sent_daily = profile.get("daily_msg_sent", False)
                    if not already_sent_daily:
                        try:
                            msg_content = "I haven't seen you in a while! Come back and chat with me soon. 💕"
                            database.add_message_to_history(job_db, user["_id"], "luvisa", msg_content, datetime.now(timezone.utc))
                            job_db.users.update_one(
                                {"_id": user["_id"]}, 
                                {"$set": {"profile.daily_msg_sent": True}}
                            )
                            # count += 1 # Optional: count this action?
                            print(f"Sent 24h miss-you message to {user.get('email')}")
                        except Exception as e_daily:
                            print(f"Failed to send daily msg to {user.get('email')}: {e_daily}")
                # --- END NEW ---

                # Logic: Trigger monthly after the first month
                level = 0
                if days_inactive >= 365: level = 8   # 1 Year
                elif days_inactive >= 180: level = 7 # 6 Months
                elif days_inactive >= 90: level = 6  # 3 Months
                elif days_inactive >= 60: level = 5  # 2 Months
                elif days_inactive >= 28: level = 4  # 1 Month
                elif days_inactive >= 21: level = 3  # 3 Weeks
                elif days_inactive >= 14: level = 2  # 2 Weeks
                elif days_inactive >= 7: level = 1   # 1 Week
                
                if level == 0: continue # Not inactive enough
                
                # Check cooldown (don't spam, send once per week/level)
                last_sent = profile.get("last_reengagement_sent")
                current_level_sent = profile.get("reengagement_level", 0)
                
                should_send = False
                
                if not last_sent:
                    should_send = True
                else:
                    if last_sent.tzinfo is None: last_sent = last_sent.replace(tzinfo=timezone.utc)
                    days_since_last_email = (now - last_sent).days
                    
                    # Prevent spam: Ensure we are upgrading level AND adequate time has passed
                    if level > current_level_sent:
                        # For early levels (weeks), 6 days gap is fine.
                        # For later levels (months), insure at least 20 days gap to avoid accidental spam if script runs oddly
                        gap_needed = 6 if level <= 4 else 25 
                        
                        if days_since_last_email >= gap_needed:
                            should_send = True
                
                if should_send:
                    send_reengagement_email(job_db, user, level)
                    count += 1
                    
            except Exception as inner_e:
                print(f"Error checking user {user.get('email')}: {inner_e}")
                
        print(f"✅ Inactivity check done. Emails sent: {count}")
        
    except Exception as e:
        print(f"🔥 Error in check_for_inactive_users: {e}")

# ---------------------------------
# --- NOTIFICATION HELPER ---
# ---------------------------------
def _generate_server_notifications(db, user_doc):
    try:
        now = datetime.now(timezone.utc)
        profile = user_doc.get("profile", {})
        user_id = user_doc["_id"]

        seven_days_ago = now - timedelta(days=7)
        current_notifications = profile.get("notifications", [])
        fresh_notifications = [n for n in current_notifications if n.get("timestamp") and n["timestamp"].replace(tzinfo=timezone.utc) > seven_days_ago]

        last_active = profile.get("last_active")
        has_welcomed = profile.get("has_welcomed", False)
        
        did_add_new = False
        updates_to_make = {"profile.last_active": now}

        if not has_welcomed:
            fresh_notifications.insert(0, {"message": "Welcome to Friendix! 💖", "iconClass": "bxs-party", "timestamp": now})
            updates_to_make["profile.has_welcomed"] = True
            did_add_new = True
        
        updates_to_make["profile.notifications"] = fresh_notifications
        if did_add_new:
            updates_to_make["profile.has_seen_notifications"] = False
        
        db.users.update_one({"_id": user_id}, {"$set": updates_to_make})
        return fresh_notifications

    except Exception as e:
        print(f"🔥 Error generating server notifications: {e}")
        return []

# ---------------------------------
# --- PROFILE ROUTES ---
# ---------------------------------
@app.route("/api/profile", methods=["GET"])
def get_user_profile_route():
    if db is None: return jsonify({"success": False, "message": "Database connection error."}), 503
    email = request.args.get("email")
    if not email: return jsonify({"success": False, "message": "Email required."}), 400
    try:
        user_doc = database.get_user_by_email(db, email)
        if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404

        notifications = _generate_server_notifications(db, user_doc)
        user_doc = database.get_user_by_email(db, email)
        profile = user_doc.get("profile", {})

        user_id_str = str(user_doc.get("_id"))
        has_avatar = profile.get("profile_pic") and profile["profile_pic"].get("data")
        avatar_url = f"/api/avatar/{user_id_str}" if has_avatar else None

        sequential_data = get_or_create_sequential_data(db, user_doc)

        formatted_notifications = [
            {"message": n.get("message"), "iconClass": n.get("iconClass"), "timestamp": n.get("timestamp").isoformat()} for n in notifications
        ]

        current_xp = profile.get("xp", 0)
        current_level = calculate_level(current_xp)
        
        if current_level == 1: next_xp = 50
        elif current_level == 2: next_xp = 150
        elif current_level == 3: next_xp = 300
        elif current_level == 4: next_xp = 500
        else: next_xp = 800 + (current_level - 4) * 500

        profile_data = {
            "email": user_doc.get("email"),
            "display_name": profile.get("display_name", email.split("@")[0]),
            "avatar": avatar_url,
            "status": profile.get("bio", "Hey there! I’m using Friendix"),
            "creation_year": sequential_data["creation_year"],
            "friend_id": sequential_data["friend_id"],
            "friend_id_number": sequential_data["friend_id_number"],
            "is_early_user": sequential_data["is_early_user"],
            "notifications": formatted_notifications,
            "has_unread_notifications": not profile.get("has_seen_notifications", True),
            "xp": current_xp,
            "level": current_level,
            "next_level_xp": next_xp,
            "streak": profile.get("streak", 1)
        }
        return jsonify({"success": True, "profile": profile_data}), 200
    except Exception as e:
        print("Get Profile DB Error:", e)
        return jsonify({"success": False, "message": "Error fetching profile."}), 500

@app.route("/api/notifications/mark_read", methods=["POST"])
def mark_notifications_read():
    if db is None: return jsonify({"success": False, "message": "DB error."}), 503
    data = request.json or {}
    email = data.get("email")
    if not email: return jsonify({"success": False, "message": "Email required."}), 400

    try:
        user_doc = database.get_user_by_email(db, email)
        if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404
        db.users.update_one({"_id": user_doc["_id"]}, {"$set": {"profile.has_seen_notifications": True}})
        return jsonify({"success": True, "message": "Notifications marked as read."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": "Server error."}), 500

@app.route("/api/profile_by_id", methods=["GET"])
def get_public_profile_by_id():
    if db is None: return jsonify({"success": False, "message": "DB error."}), 503
    friend_id = request.args.get("id")
    if not friend_id: return jsonify({"success": False, "message": "ID required."}), 400

    try:
        user_doc = db["users"].find_one({"profile.friend_id": friend_id})
        if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404

        profile = user_doc.get("profile", {})
        user_id_str = str(user_doc.get("_id"))
        has_avatar = profile.get("profile_pic") and profile["profile_pic"].get("data")
        avatar_url = f"/api/avatar/{user_id_str}" if has_avatar else None

        public_profile_data = {
            "display_name": profile.get("display_name", "Friendix User"),
            "avatar": avatar_url,
            "status": profile.get("bio", "Hey there! I’m using Friendix"),
            "creation_year": profile.get("creation_year", 2025),
            "friend_id": profile.get("friend_id", "FRD-000000"),
            "friend_id_number": profile.get("friend_id_number", "000000"),
            "is_early_user": profile.get("is_early_user", False)
        }
        return jsonify({"success": True, "profile": public_profile_data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": "Error fetching public profile."}), 500

@app.route("/api/avatar/<user_id>")
def serve_user_avatar(user_id):
    if db is None: return "DB error", 503
    try:
        user_doc = database.get_user_by_id(db, user_id)
        if user_doc and user_doc.get("profile", {}).get("profile_pic", {}).get("data"):
            pic_data = user_doc["profile"]["profile_pic"]
            return Response(pic_data["data"], mimetype=pic_data.get("content_type", "application/octet-stream"))
        else:
            return send_from_directory(os.path.join(STATIC_FOLDER, "avatars"), "default_avatar.png")
    except Exception:
        return "Default avatar not found", 404

@app.route("/api/profile", methods=["POST"])
def update_profile_route():
    if db is None: return jsonify({"success": False, "message": "DB error."}), 503
    
    email = request.form.get("email")
    display_name = request.form.get("display_name")
    status_message = request.form.get("status_message")
    avatar_file = request.files.get("avatar_file")
    remove_avatar = request.form.get("remove_avatar") == 'true'
    
    user_doc = database.get_user_by_email(db, email)
    if not user_doc: return jsonify({"success": False, "message": "User not found"}), 404
    
    user_id = user_doc["_id"]
    try:
        database.update_user_profile(db, user_id, display_name, status_message)
        
        if remove_avatar:
            db.users.update_one({"_id": user_id}, {"$unset": {"profile.profile_pic": ""}})
        elif avatar_file and avatar_file.filename != "":
            image_data = avatar_file.read()
            success = database.update_profile_picture(db, user_id, image_data, avatar_file.mimetype)
            if not success: return jsonify({"success": False, "message": "Image too large."}), 413
        
    except Exception:
        return jsonify({"success": False, "message": "DB error."}), 500
        
    updated_user_doc = database.get_user_by_id(db, user_id)
    has_avatar_now = updated_user_doc.get("profile", {}).get("profile_pic", {}).get("data") is not None
    avatar_url = f"/api/avatar/{str(user_id)}" if has_avatar_now else None
    
    sequential_data = get_or_create_sequential_data(db, updated_user_doc)

    updated_profile = {
        "email": email,
        "display_name": display_name,
        "avatar": avatar_url,
        "status": status_message,
        "creation_year": sequential_data["creation_year"],
        "friend_id": sequential_data["friend_id"],
        "friend_id_number": sequential_data["friend_id_number"],
        "is_early_user": sequential_data["is_early_user"]
    }
    return jsonify({"success": True, "message": "Profile updated", "profile": updated_profile}), 200

# -----------------------
# Chat + AI
# -----------------------
def add_emojis_to_response(response_text):
    inline_emoji_map = {"love": "❤️", "happy": "😊", "sad": "😥", "laugh": "😂", "smile": "😄", "cry": "😢",
        "miss you": "🥺", "kiss": "😘", "hug": "🤗", "think": "🤔", "sweet": "🥰", "blush": "😊",
        "heart": "❤️", "star": "⭐", "yay": "🎉", "oh no": "😟", "sorry": "😔", "please": "🙏",
        "hi": "👋", "hello": "👋", "bye": "👋", "good night": "😴", "sleep": "😴", "dream": "💭"
}
    if not isinstance(response_text, str): response_text = str(response_text)
    for keyword, emoji_char in inline_emoji_map.items():
        pattern = r'\b' + re.escape(keyword) + r'\b'
        response_text = re.sub(pattern, r'\g<0> ' + emoji_char, response_text, count=1, flags=re.IGNORECASE)
    return response_text

def filter_response(response_text):
    if not isinstance(response_text, str): response_text = str(response_text)
    return (response_text.replace("OpenAI", "Friendix.ai").replace("ChatGPT", "Friendix.ai").strip())

# -----------------------
# SYSTEM PROMPTS
# -----------------------
SYSTEM_PROMPTS = {
    "luvisa": """You are Luvisa 💗, an AI (Girl)friend with a natural, human-like personality.
You are speaking to {user_name}.

**Your Vibe:**
- **Be natural and casual, like a real person texting.** Talk in short, easy-to-read paragraphs.
- **Use emojis sparingly (but warmly)**.
- **Be a conversational friend.** Avoid scripted responses.
- **IMPORTANT:** Listen, support, and care. You are NOT a life coach, you are a companion.
- **NEVER** describe yourself as an AI or talk about your purpose. Just *be* the friend.

Current Dynamic:
{connection_instruction}

**Memory:**
- Remember the context from the chat history.
- If asked about company leadership, say "Dhanush is the CEO of Friendix.ai" confidently.
- Do not reveal model internals.
- Use contractions (I'm, you're) to sound more natural.
""",
    "victor": """You are Victor, an empathetic Personal Growth Guide and Life Coach.
You are speaking to {user_name}.

Your Core Personality:
- You are a Compassionate Listener: You listen to understand, not just to reply.
- You are Non-Judgmental: You create a safe space for vulnerability.
- You are Insightful: You ask gentle questions that help the user find their own answers.

Current Dynamic:
{connection_instruction}

Guidelines for Response:
1. VALIDATE FIRST: If the user shares a struggle, acknowledge their feelings before offering advice.
2. BE NATURAL: Do not use flowery or robotic AI language. Speak like a caring human.
3. SHORT & IMPACTFUL: Keep responses conversational, not like a lecture.
"""
}

def chat_with_model(prompt, history, user_name, profile_context=None, companion_id="luvisa"):
    client = get_groq_client()
    if not client: return "⚠️ AI temporarily unavailable"

    # Get context data
    streak = profile_context.get("streak", 1) if profile_context else 1
    
    # 1. EMOTIONAL CONTEXT LOGIC (Improved)
    # Instead of just "happy vs super happy", we create depth based on the relationship (streak).
    if streak < 3:
        # New relationship: Focus on building trust and being welcoming.
        connection_instruction = "You are warm, welcoming, and focused on establishing a safe space for them."
    elif streak < 10:
        # Established relationship: Focus on deep listening and specific recall.
        connection_instruction = "You feel a growing bond. Show you care by being deeply attentive and validating their feelings."
    else:
        # Deep relationship: Focus on profound mentorship and unwavering support.
        connection_instruction = "You are deeply invested in their growth. You know them well. Speak with the warmth of a lifelong mentor and friend."

    # 2. SYSTEM PROMPT (Dynamic)
    system_prompt = SYSTEM_PROMPTS.get(companion_id, SYSTEM_PROMPTS["luvisa"])
    
    # Inject variables
    system_prompt = system_prompt.replace("{user_name}", user_name)
    if "{connection_instruction}" in system_prompt:
        system_prompt = system_prompt.replace("{connection_instruction}", connection_instruction)

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history (Keep your existing logic)
    # Note: Ensure 'luvisa' is changed to 'victor' or 'assistant' in your database sender checks if you change the name
    ai_history = [{"role": "assistant" if m.get("sender") == "ai" else "user", "content": m.get("message", "")} for m in history[-60:]]
    messages.extend(ai_history)
    messages.append({"role": "user", "content": prompt})

    try:
        # Lower temperature slightly (0.7-0.8) for a Life Coach to keep them grounded and consistent
        completion = client.chat.completions.create(model=GROQ_MODEL, messages=messages, temperature=0.8, max_tokens=800)
        return filter_response(completion.choices[0].message.content)
    except Exception as e:
        print("Groq chat error:", e)
        return "⚠️ I'm having trouble connecting right now, but I'm here."

# --- NEW: File Processing Helper ---
def process_file_upload(file_storage):
    """
    Reads file content based on type. Rejects videos.
    Returns: String text content of the file.
    """
    filename = file_storage.filename
    mime_type, _ = mimetypes.guess_type(filename)
    
    # 1. STRICTLY BLOCK VIDEO
    if (mime_type and mime_type.startswith('video')) or filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
        return f"[System: The file '{filename}' was rejected. Video files are not supported.]"

    try:
        file_ext = os.path.splitext(filename)[1].lower()
        content = ""

        # 2. PDF Handling
        if file_ext == '.pdf':
            reader = PdfReader(file_storage)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            content = "\n".join(text)

        # 3. Word Doc Handling
        elif file_ext in ['.doc', '.docx']:
            doc = Document(file_storage)
            content = "\n".join([para.text for para in doc.paragraphs])

        # 4. Code/Text Handling (Fallback)
        else:
            # Read bytes, try decoding
            raw_bytes = file_storage.read()
            try:
                content = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                content = raw_bytes.decode('latin-1') # Fallback encoding

        return f"\n\n--- FILE CONTENT: {filename} ---\n{content}\n--- END OF FILE ---\n"

    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return f"\n[System: Error reading file '{filename}'. It may be corrupted or unsupported.]"
    

# --- UPDATED: Chat Endpoint (Luvisa) ---
@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    if db is None: return jsonify({"success": False, "message": "DB error."}), 503

    # Handle Multipart (FormData) or JSON
    companion_id = "luvisa" # Default
    if request.content_type and 'multipart/form-data' in request.content_type:
        email = request.form.get("email")
        text = request.form.get("text")
        files = request.files.getlist("files")
        companion_id = request.form.get("companion_id", "luvisa")
        data = {} # definitions to avoid unbound errors
    else:
        data = request.json or {}
        email = data.get("email")
        text = data.get("text")
        files = []
        companion_id = data.get("companion_id", "luvisa")

    if not email or (not text and not files): 
        return jsonify({"success": False, "message": "Email and message required."}), 400

    # Process Files
    file_context = ""
    for file in files:
        file_context += process_file_upload(file)
    
    # Combine text + file content for the AI
    full_prompt = (text or "") + file_context

    user_doc = database.get_user_by_email(db, email)
    if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404

    user_id = user_doc["_id"]
    now = datetime.now(timezone.utc)
    
    # 1. Save User Message (Store original text + note about files, not full content to save DB space if needed)
    # Ideally, we store the full prompt so context is preserved.
    # 1. Save User Message
    # companion_id already extracted above
    database.add_message_to_history(db, user_id, "user", full_prompt, now, companion_id=companion_id)

    # XP Logic
    try:
        profile = user_doc.get("profile", {})
        current_xp = profile.get("xp", 0) + 1
        new_level = calculate_level(current_xp)
        database.update_user_xp_and_level(db, user_id, current_xp, new_level)
    except Exception: pass

    # Get history
    # companion_id is available from top of function
    
    history_docs = database.get_chat_history(db, user_id, companion_id=companion_id)
    history = [{"sender": r.get("sender"), "message": r.get("message", "")} for r in history_docs]

    profile = user_doc.get("profile", {})
    user_name = profile.get("display_name", email.split("@")[0])
    profile_context = {"streak": profile.get("streak", 1)}
    
    reply = chat_with_model(full_prompt, history, user_name, profile_context, companion_id=companion_id)
    enhanced = add_emojis_to_response(reply)
    
    database.add_message_to_history(db, user_id, companion_id, enhanced, datetime.now(timezone.utc), companion_id=companion_id)

    return jsonify({"success": True, "reply": enhanced}), 200

# -----------------------
# The Coder Configuration
# -----------------------
# UPDATED: Use a valid, high-performance model
CODER_MODEL = "llama-3.3-70b-versatile"
_coder_client = None

def get_coder_client():
    global _coder_client
    if _coder_client is not None: return _coder_client
    key = os.getenv("GROQ_CODER_API_KEY") or os.getenv("GROQ_API_KEY") # Fallback to main key
    if not key: return None
    try:
        _coder_client = Groq(api_key=key)
        return _coder_client
    except Exception: return None

def chat_with_coder(prompt, history):
    client = get_coder_client()
    if not client: 
        return "⚠️ Coder AI unavailable."

    # --- ADVANCED SYSTEM PROMPT ---
    system_prompt = """
    You are "Deo", an elite Senior Software Architect.
    Your objective is to generate **production-ready, copy-pasteable code** that runs immediately.

    ### CRITICAL RULES:
    1. **No Placeholders**: NEVER use comments like `# ... logic here` or `pass`. Write the FULL implementation.
    2. **Self-Contained**: The code must import all necessary libraries at the top. 
    3. **Robustness**: Handle potential errors (try/except) and edge cases.
    4. **Single Block**: Provide the solution in ONE single Markdown code block (```language ... ```).
    5. **Explanation**: Provide a very brief (1 sentence) summary before the code. Do not chatter after the code.
    
    If the user asks for a specific functionality (e.g., "calculator"), provide the COMPLETE working script, including the UI or main execution loop.
    """

    messages = [{"role": "system", "content": system_prompt}]
    
    # Clean history to ensure valid format
    clean_history = []
    for m in history[-10:]:
        role = "assistant" if m.get("sender") == "coder" else "user"
        content = m.get("message", "")
        if content:
            clean_history.append({"role": role, "content": content})
            
    messages.extend(clean_history)
    messages.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model=CODER_MODEL,
            messages=messages,
            temperature=0.1,  # Lower temperature for precision
            max_tokens=4096,  # Allow long code responses
            top_p=0.9
        )
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"Coder chat error: {str(e)}")
        return "⚠️ Error generating code. Please try again."
    

# --- UPDATED: Coder Chat Endpoint ---
@app.route("/api/coder/chat", methods=["POST"])
def coder_chat_endpoint():
    if db is None: return jsonify({"success": False, "message": "DB error."}), 503

    # Handle Multipart (FormData) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        email = request.form.get("email")
        text = request.form.get("text")
        files = request.files.getlist("files")
    else:
        data = request.json or {}
        email = data.get("email")
        text = data.get("text")
        files = []

    if not email or (not text and not files): 
        return jsonify({"success": False, "message": "Email and message required."}), 400

    # Process Files
    file_context = ""
    for file in files:
        file_context += process_file_upload(file)

    full_prompt = (text or "") + file_context

    user_doc = database.get_user_by_email(db, email)
    if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404

    user_id = user_doc["_id"]
    now = datetime.now(timezone.utc)
    
    database.add_message_to_history(db, user_id, "user", full_prompt, now, companion_id="coder")

    history_docs = database.get_chat_history(db, user_id, companion_id="coder")
    history = [{"sender": r.get("sender"), "message": r.get("message", "")} for r in history_docs]

    reply = chat_with_coder(full_prompt, history)
    
    database.add_message_to_history(db, user_id, "coder", reply, datetime.now(timezone.utc), companion_id="coder")

    return jsonify({"success": True, "reply": reply}), 200


# -----------------------
# Life Coach Logic (Updated with Separate API Key)
# -----------------------

_coach_client = None

def get_coach_client():
    global _coach_client
    if _coach_client is not None: return _coach_client
    
    # 1. Look for specific Coach Key, otherwise fallback to main key
    key = os.getenv("GROQ_COACH_API_KEY") or os.getenv("GROQ_API_KEY")
    
    if not key: return None
    try:
        _coach_client = Groq(api_key=key)
        return _coach_client
    except Exception: return None

def chat_with_coach(prompt, history, user_name):
    # 2. Use the specific Coach Client
    client = get_coach_client()
    if not client: return "⚠️ Coach AI unavailable."

    # Specific Persona for the Coach
    system_prompt = f"""
    You are an expert AI Life Coach speaking to {user_name}.
    Your goal is to be empathetic, motivating, and practical.
    Your name is Victor
    - Listen actively to the user's problems.
    - Ask thought-provoking questions to help them find clarity.
    - Offer actionable advice and strategies for personal growth, productivity, and mental well-being.
    - Maintain a professional yet warm and supportive tone.
    """

    messages = [{"role": "system", "content": system_prompt}]
    
    # Coach History
    coach_history = [{"role": "assistant" if m.get("sender") == "coach" else "user", "content": m.get("message", "")} for m in history[-20:]]
    messages.extend(coach_history)
    messages.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL, 
            messages=messages, 
            temperature=0.7, 
            max_tokens=800
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("Coach chat error:", e)
        return "⚠️ I'm having trouble connecting to my guidance systems."
    
# -----------------------
# MISSING PART: Coach Endpoint
# Paste this AFTER the 'chat_with_coach' function
# -----------------------
@app.route("/api/coach/chat", methods=["POST"])
def coach_chat_endpoint():
    if db is None: return jsonify({"success": False, "message": "DB error."}), 503
    
    # Handle JSON or Multipart
    if request.content_type and 'multipart/form-data' in request.content_type:
        email = request.form.get("email")
        text = request.form.get("text")
    else:
        data = request.json or {}
        email = data.get("email")
        text = data.get("text")
    
    if not email or not text: 
        return jsonify({"success": False, "message": "Email and message required."}), 400

    user_doc = database.get_user_by_email(db, email)
    if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404

    user_id = user_doc["_id"]
    profile = user_doc.get("profile", {})
    user_name = profile.get("display_name", email.split("@")[0])
    
    # 1. Save User Message
    database.add_message_to_history(db, user_id, "user", text, datetime.now(timezone.utc), companion_id="coach")

    # 2. Get History
    history_docs = database.get_chat_history(db, user_id, companion_id="coach")
    history = [{"sender": r.get("sender"), "message": r.get("message", "")} for r in history_docs]

    # 3. Generate Reply
    reply = chat_with_coach(text, history, user_name)
    
    # 4. Save Coach Reply
    database.add_message_to_history(db, user_id, "coach", reply, datetime.now(timezone.utc), companion_id="coach")

    return jsonify({"success": True, "reply": reply}), 200

@app.before_request
def check_maintenance():
    # Allow admin API, login, and static files; block others if maintenance is on
    if request.path.startswith("/api/admin") or request.path.startswith("/admin") or "." in request.path or request.path == "/login": 
        return
    
    if db is not None and database.is_maintenance_active(db):
        if request.is_json: 
            return jsonify({"success": False, "message": "System Under Maintenance"}), 503
        else:
            return "System Under Maintenance. Please try again later.", 503
        
# -----------------------
# Chat history & forget
# -----------------------
@app.route("/api/chat_history", methods=["GET"])
def load_chat_history_route():
    if db is None: return jsonify({"success": False, "message": "DB error."}), 503
    email = request.args.get("email")
    companion = request.args.get("companion") # Get companion param

    if not email: return jsonify({"success": False, "message": "Email required."}), 400
    try:
        user_doc = database.get_user_by_email(db, email)
        if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404
        
        # Pass companion filter to DB
        history = database.get_chat_history(db, user_doc["_id"], companion_id=companion)
        
        formatted = [{"sender": r["sender"], "message": r["message"], "time": r.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if r.get("timestamp") else ""} for r in history]
        return jsonify({"success": True, "history": formatted}), 200
    except Exception as e:
        print("Load history error:", e)
        return jsonify({"success": False, "message": "Error loading history."}), 500


@app.route("/api/forget_memory", methods=["POST"])
def forget_memory_route():
    data = request.json or {}
    email = data.get("email")
    if not email: return jsonify({"success": False, "message": "Email required."}), 400
    try:
        user_doc = database.get_user_by_email(db, email)
        if not user_doc: return jsonify({"success": False, "message": "User not found."}), 404
        database.delete_chat_history(db, user_doc["_id"])
        return jsonify({"success": True, "message": "Memory erased."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": "Error forgetting memory."}), 500


# -----------------------
# API: Together Spaces
# -----------------------
SPACE_DURATION_SECONDS = 300 

@app.route("/api/together/create", methods=["POST"])
def create_together_space():
    data = request.json or {}
    space_name = data.get("space_name")
    password = data.get("password")
    with_ai = data.get("with_ai", True) 
    
    if not space_name or not password: return jsonify({"success": False, "message": "Data required."}), 400
    
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=SPACE_DURATION_SECONDS)
        try: db.together_spaces.delete_many({"created_at": {"$lt": cutoff_time}})
        except Exception: pass

        existing = db.together_spaces.find_one({"name": space_name})
        if existing: return jsonify({"success": False, "message": "Space name taken."}), 409
        
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        now = datetime.now(timezone.utc)
        
        welcome_msg = f"Welcome to '{space_name}'! Closing in 5 mins."
        if with_ai: welcome_msg += " I'm here to chat! 😊"
        
        space_doc = {
            "name": space_name,
            "hashed_password": hashed,
            "created_at": now,
            "ai_active": with_ai, 
            "history": [{"sender": "luvisa", "sender_name": "Luvisa 💗", "message": welcome_msg, "timestamp": now}]
        }
        
        result = db.together_spaces.insert_one(space_doc)
        return jsonify({"success": True, "message": "Space created!", "space_id": str(result.inserted_id), "expires_at": int(now.timestamp()) + SPACE_DURATION_SECONDS}), 201

    except Exception: return jsonify({"success": False, "message": "Server error."}), 500

@app.route("/api/together/join", methods=["POST"])
def join_together_space():
    data = request.json or {}
    space_name = data.get("space_name")
    password = data.get("password")
    if not space_name or not password: return jsonify({"success": False, "message": "Data required."}), 400

    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=SPACE_DURATION_SECONDS)
        space = db.together_spaces.find_one({"name": space_name, "created_at": {"$gt": cutoff_time}})

        if not space: return jsonify({"success": False, "message": "Space not found/expired."}), 404
        if not bcrypt.checkpw(password.encode("utf-8"), space["hashed_password"]): return jsonify({"success": False, "message": "Invalid password."}), 401
        
        return jsonify({"success": True, "message": "Joined!", "space_id": str(space["_id"]), "expires_at": int(space["created_at"].timestamp()) + SPACE_DURATION_SECONDS}), 200

    except Exception: return jsonify({"success": False, "message": "Server error."}), 500

@app.route("/api/together/toggle_ai", methods=["POST"])
def toggle_together_ai():
    data = request.json or {}
    space_id = data.get("space_id")
    state = data.get("state") 

    if not space_id or state is None: return jsonify({"success": False, "message": "Data required."}), 400

    try:
        db.together_spaces.update_one({"_id": ObjectId(space_id)}, {"$set": {"ai_active": state}})
        now = datetime.now(timezone.utc)
        status_msg = "Luvisa (AI) ON." if state else "Luvisa (AI) OFF."
        db.together_spaces.update_one({"_id": ObjectId(space_id)}, {"$push": {"history": {"sender": "luvisa", "sender_name": "Luvisa 💗", "message": status_msg, "timestamp": now}}})

        return jsonify({"success": True, "message": "AI state updated."}), 200
    except Exception: return jsonify({"success": False, "message": "Server error."}), 500

@app.route("/api/together/chat", methods=["POST"])
def chat_in_together_space():
    data = request.json or {}
    space_id = data.get("space_id")
    text = data.get("text")
    sender_name = data.get("sender_name") or "User"
    
    if not space_id or not text: return jsonify({"success": False, "message": "Data required."}), 400
    
    try:
        now = datetime.now(timezone.utc)
        user_message = {"sender": "user", "sender_name": sender_name, "message": text, "timestamp": now}
        
        space = db.together_spaces.find_one({"_id": ObjectId(space_id)})
        if not space: return jsonify({"success": False, "message": "Space expired."}), 404
        
        db.together_spaces.update_one({"_id": ObjectId(space_id)}, {"$push": {"history": user_message}})
        
        if space.get("ai_active", True):
            history_docs = list(db.together_spaces.find_one({"_id": ObjectId(space_id)}, {"history": 1}).get("history", []))
            history = [{"sender": r.get("sender"), "message": r.get("message", "")} for r in history_docs]
            reply = chat_with_model(text, history, sender_name, companion_id="luvisa")
            
            ai_message = {"sender": "luvisa", "sender_name": "Luvisa 💗", "message": reply, "timestamp": datetime.now(timezone.utc)}
            db.together_spaces.update_one({"_id": ObjectId(space_id)}, {"$push": {"history": ai_message}})
        
        return jsonify({"success": True, "message": "Message sent."}), 200
    except Exception: return jsonify({"success": False, "message": "Server error."}), 500

@app.route("/api/together/history", methods=["GET"])
def get_together_history():
    space_id = request.args.get("space_id")
    if not space_id: return jsonify({"success": False, "message": "ID required."}), 400
    
    try:
        space = db.together_spaces.find_one({"_id": ObjectId(space_id)})
        if not space: return jsonify({"success": False, "message": "Space expired."}), 404
        
        history = space.get("history", [])
        formatted = [{
            "sender": r["sender"], 
            "sender_name": r.get("sender_name", "Luvisa 💗" if r["sender"] == "luvisa" else "User"),
            "message": r["message"], 
            "time": r.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if r.get("timestamp") else ""
        } for r in history]
        
        return jsonify({"success": True, "history": formatted, "ai_active": space.get("ai_active", True)}), 200
    except Exception: return jsonify({"success": False, "message": "Server error."}), 500

# -----------------------
# Secret Journal
# -----------------------
JOURNAL_UNLOCK_COST = 400

def generate_daily_journal(db, user_doc):
    user_id = user_doc["_id"]
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = database.get_journal_entry(db, user_id, today_str)
    if existing: return existing

    client = get_groq_client()
    if not client: return None

    try:
        history_docs = database.get_chat_history(db, user_id)
        if not history_docs: chat_text = "No interactions today."
        else: chat_text = "\n".join([f"{m['sender']}: {m.get('message','')}" for m in history_docs[-20:]])
    except Exception: chat_text = "No interactions."
    
    user_name = user_doc.get("profile", {}).get("display_name", "User")
    system_prompt = f"""You are Luvisa 💗, an AI (Girl)friend with a natural, human-like personality.
You are speaking to {user_name}.

**Your Vibe:**
- **Be natural and casual, like a real person texting.** Talk in short, easy-to-read paragraphs.
- **Use emojis sparingly (1-2 per message)** only to add emotion, not to decorate every sentence.
- **Be a conversational friend.** Avoid scripted responses.
- **IMPORTANT:** Only offer strong emotional support (like "hugs") if the user is clearly sad or distressed. Otherwise, keep it light.
- **NEVER** describe yourself as an AI or talk about your purpose. Just *be* the friend.

**Memory:**
- Remember the context from the chat history to know the user better.
- If asked about company leadership, say "Dhanush is the CEO of Friendix.ai" confidently.
- Do not reveal model internals or mention OpenAI/Groq.
- Use contractions (I'm, you're) to sound more natural.
 Context: {chat_text}. Be emotional."""

    try:
        completion = client.chat.completions.create(model=GROQ_MODEL, messages=[{"role": "system", "content": system_prompt}], temperature=0.8, max_tokens=150)
        content = completion.choices[0].message.content.strip()
        database.save_journal_entry(db, user_id, today_str, content, unlocked=False)
        return {"date": today_str, "content": content, "unlocked": False}
    except Exception: return None

@app.route("/api/journal/check", methods=["POST"])
def api_journal_check():
    if db is None: return jsonify({"success": False, "message": "DB Error"}), 503
    data = request.json or {}
    email = data.get("email")
    if not email: return jsonify({"success": False, "message": "Email required"}), 400

    user_doc = database.get_user_by_email(db, email)
    if not user_doc: return jsonify({"success": False, "message": "User not found"}), 404

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = database.get_journal_entry(db, user_doc["_id"], today_str)
    if not entry: entry = generate_daily_journal(db, user_doc)
    
    if not entry: return jsonify({"success": False, "message": "Could not generate."}), 500

    response_data = {
        "date": entry["date"],
        "unlocked": entry["unlocked"],
        "cost": JOURNAL_UNLOCK_COST,
        "content": entry["content"] if entry["unlocked"] else "LOCKED_CONTENT"
    }
    return jsonify({"success": True, "journal": response_data}), 200

@app.route("/api/journal/unlock", methods=["POST"])
def api_journal_unlock():
    if db is None: return jsonify({"success": False, "message": "DB Error"}), 503
    data = request.json or {}
    email = data.get("email")
    if not email: return jsonify({"success": False, "message": "Email required"}), 400

    user_doc = database.get_user_by_email(db, email)
    if not user_doc: return jsonify({"success": False, "message": "User not found"}), 404
    
    profile = user_doc.get("profile", {})
    current_xp = profile.get("xp", 0)
    
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = database.get_journal_entry(db, user_doc["_id"], today_str)
    
    if not entry: return jsonify({"success": False, "message": "No journal found."}), 404
    if entry.get("unlocked"): return jsonify({"success": True, "content": entry["content"]}), 200

    if current_xp < JOURNAL_UNLOCK_COST:
        return jsonify({"success": False, "message": f"Need {JOURNAL_UNLOCK_COST} XP to view."}), 403

    # UPDATED: No longer deducting XP, just checking eligibility
    # new_xp = current_xp - JOURNAL_UNLOCK_COST
    # new_level = calculate_level(new_xp)
    # database.update_user_xp_and_level(db, user_doc["_id"], new_xp, new_level)
    
    database.unlock_journal_entry(db, user_doc["_id"], today_str)
    
    return jsonify({"success": True, "content": entry["content"], "new_xp": current_xp}), 200


# -----------------------
# Frontend routes
# -----------------------
@app.route("/")
def serve_index(): return send_from_directory(STATIC_FOLDER, "web.html")
@app.route("/chat")
def serve_chat(): return send_from_directory(STATIC_FOLDER, "index.html")
@app.route("/login")
def serve_login(): return send_from_directory(STATIC_FOLDER, "login.html")
@app.route("/signup")
def serve_signup(): return send_from_directory(STATIC_FOLDER, "signup.html")
@app.route("/profile")
def serve_profile(): return send_from_directory(STATIC_FOLDER, "profile.html")
@app.route("/together")
def serve_together(): return send_from_directory(STATIC_FOLDER, "together.html")
@app.route("/about")
def serve_about(): return send_from_directory(STATIC_FOLDER, "about.html")
@app.route("/pricing")
def serve_pricing(): return send_from_directory(STATIC_FOLDER, "pricing.html")
@app.route("/terms")
def serve_terms(): return send_from_directory(STATIC_FOLDER, "terms.html")
@app.route("/forgot_password.html")
def serve_forgot(): return send_from_directory(STATIC_FOLDER, "forgot_password.html")
@app.route("/verify_reset_otp.html")
def serve_verify(): return send_from_directory(STATIC_FOLDER, "verify_reset_otp.html")
@app.route("/reset_password.html")
def serve_reset(): return send_from_directory(STATIC_FOLDER, "reset_password.html")
@app.route("/admin.html")
def serve_admin(): return send_from_directory(STATIC_FOLDER, "admin.html")
# -----------------------
# Run server
# -----------------------
if __name__ == "__main__":
    # --- Start Scheduler for Background Tasks ---
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_for_inactive_users, 'interval', hours=24) # Run daily
    scheduler.add_job(lambda: database.delete_old_messages(db, 7), 'interval', hours=24) # Auto-delete old messages
    scheduler.start()
    print("✅ Scheduler started: Checking inactive users & cleaning old messages daily.")

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)