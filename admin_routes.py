import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response
import database

# Try importing psutil for system health (optional)
try:
    import psutil
except ImportError:
    psutil = None

# Create a Blueprint (a modular group of routes)
admin_bp = Blueprint('admin', __name__)

# Initialize DB connection for this module
try:
    database.load_config()
    db = database.get_db()
except Exception as e:
    print("🔥 Admin Route DB Error:", e)
    db = None

# --- ADMIN HELPERS ---

def verify_admin_request(req):
    """Checks Email and Password against Database."""
    email = req.args.get("admin_email") or (req.json and req.json.get("admin_email"))
    password = req.headers.get("x-admin-password")
    
    if not email or not password: 
        return False
        
    return database.verify_admin_credentials(db, email, password)

def get_admin_email(req): 
    return req.args.get("admin_email") or (req.json and req.json.get("admin_email"))

# --- ADMIN ROUTES ---

@admin_bp.route("/api/admin/verify_access", methods=["POST"])
def api_admin_verify_access():
    if verify_admin_request(request):
        database.log_admin_action(db, get_admin_email(request), "LOGIN", "Admin logged in")
        return jsonify({"success": True, "message": "Access Granted"})
    return jsonify({"success": False, "message": "Invalid Credentials"}), 401

@admin_bp.route("/api/admin/dashboard", methods=["GET"])
def api_admin_dashboard():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    stats = database.get_system_stats(db)
    return jsonify({"success": True, "stats": stats})

@admin_bp.route("/api/admin/analytics/growth", methods=["GET"])
def api_admin_growth_chart():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    data = database.get_daily_signups(db)
    return jsonify({"success": True, "chartData": data})

@admin_bp.route("/api/admin/system/health", methods=["GET"])
def api_admin_health():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    
    cpu = 0; ram = 0; disk = 0
    if psutil:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
    else:
        # Mock data if psutil missing
        cpu = 15; ram = 40; disk = 55
        
    return jsonify({"success": True, "health": {"cpu": cpu, "ram": ram, "disk": disk}})

@admin_bp.route("/api/admin/users", methods=["GET"])
def api_admin_users():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    users = database.get_all_users_admin(db, limit=100)
    return jsonify({"success": True, "users": users})

@admin_bp.route("/api/admin/users/<user_id>", methods=["DELETE"])
def api_admin_delete_user(user_id):
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    if database.delete_user_complete(db, user_id):
        database.log_admin_action(db, get_admin_email(request), "DELETE_USER", f"Deleted user ID {user_id}")
        return jsonify({"success": True})
    return jsonify({"success": False}), 500

@admin_bp.route("/api/admin/users/<user_id>/ban", methods=["POST"])
def api_admin_ban_user(user_id):
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    status = database.toggle_user_ban(db, user_id)
    if status is not None:
        action = "BAN_USER" if status else "UNBAN_USER"
        database.log_admin_action(db, get_admin_email(request), action, f"User ID {user_id}")
        return jsonify({"success": True, "banned": status})
    return jsonify({"success": False}), 500

@admin_bp.route("/api/admin/users/<user_id>/chats", methods=["GET"])
def api_admin_view_chats(user_id):
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    chats = database.get_chat_history(db, user_id, companion_id='all')
    formatted = [{"sender": c["sender"], "message": c["message"], "time": c.get("timestamp").strftime("%Y-%m-%d %H:%M") if c.get("timestamp") else ""} for c in chats]
    return jsonify({"success": True, "chats": formatted})

@admin_bp.route("/api/admin/broadcast", methods=["POST"])
def api_admin_broadcast():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    data = request.json
    count = database.broadcast_notification(db, data.get("message"), data.get("filters"))
    database.log_admin_action(db, get_admin_email(request), "BROADCAST", f"Sent to {count} users")
    return jsonify({"success": True, "message": f"Sent to {count} users."})

    database.log_admin_action(db, get_admin_email(request), "MAINTENANCE", f"Set to {active}")
    return jsonify({"success": True, "status": active})

@admin_bp.route("/api/admin/moderation/flagged", methods=["GET"])
def api_admin_moderation():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    messages = database.get_flagged_messages(db)
    return jsonify({"success": True, "messages": messages})

@admin_bp.route("/api/admin/logs", methods=["GET"])
def api_admin_logs():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    logs = database.get_admin_logs(db)
    return jsonify({"success": True, "logs": logs})

@admin_bp.route("/api/admin/feedback", methods=["GET"])
def api_admin_feedback():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    feedback = database.get_all_feedback(db)
    return jsonify({"success": True, "feedback": feedback})

@admin_bp.route("/api/admin/messages/search", methods=["GET"])
def api_admin_search_messages():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    query = request.args.get("query", "")
    messages = database.search_chat_messages(db, query)
    return jsonify({"success": True, "messages": messages})

@admin_bp.route("/api/admin/users/<user_id>/update", methods=["POST"])
def api_admin_update_user(user_id):
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    data = request.json
    success = database.admin_update_user(db, user_id, data.get("name"), data.get("xp"), data.get("level"), data.get("subscription"), password=data.get("password"))
    if success:
        database.log_admin_action(db, get_admin_email(request), "UPDATE_USER", f"Updated user {user_id}")
    if success:
        database.log_admin_action(db, get_admin_email(request), "UPDATE_USER", f"Updated user {user_id}")
    return jsonify({"success": success})

@admin_bp.route("/api/admin/users/<user_id>/promote", methods=["POST"])
def api_admin_promote_user(user_id):
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    if database.promote_user_to_admin(db, user_id):
        database.log_admin_action(db, get_admin_email(request), "PROMOTE_USER", f"Promoted user {user_id}")
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Failed to promote"}), 500



@admin_bp.route("/api/admin/export/users", methods=["GET"])
def api_admin_export_users():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    csv_data = database.generate_users_csv(db)
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=users_export.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@admin_bp.route("/api/admin/helpers", methods=["GET"])
def api_admin_list_helpers():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    admins = database.get_all_admins(db)
    return jsonify({"success": True, "admins": admins})

@admin_bp.route("/api/admin/helpers", methods=["POST"])
def api_admin_create_helper():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not email or not password: return jsonify({"success": False, "message": "Missing fields"}), 400
    
    database.create_new_admin(db, email, password)
    database.log_admin_action(db, get_admin_email(request), "CREATE_ADMIN", f"Created admin {email}")
    return jsonify({"success": True})

@admin_bp.route("/api/admin/helpers", methods=["DELETE"])
def api_admin_delete_helper():
    if not verify_admin_request(request): return jsonify({"success": False}), 401
    email = request.args.get("email")
    if not email: return jsonify({"success": False}), 400
    
    # Prevent self-deletion
    if email == get_admin_email(request):
        return jsonify({"success": False, "message": "cannot delete yourself"}), 403

    success = database.delete_admin(db, email)
    if success:
        database.log_admin_action(db, get_admin_email(request), "DELETE_ADMIN", f"Deleted admin {email}")
    return jsonify({"success": success})