import os
import bcrypt
import mimetypes
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
from bson.binary import Binary, BINARY_SUBTYPE
from pymongo.errors import DuplicateKeyError, OperationFailure

# --- Config and Connection ---

def load_config():
    """Load .env file."""
    load_dotenv()

def get_db():
    """Connects to MongoDB and returns the database object."""
    uri = os.getenv("MONGODB_URI")
    if not uri: return None
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client.luvisa

# --- User Operations ---

def register_user(db, email, password):
    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_document = {
            "email": email,
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow(),
            "profile": {
                "display_name": email.split('@')[0],
                "bio": "Hey there! I’m using Friendix",
                "xp": 0, "level": 1, "streak": 1,
                "notifications": [], "has_seen_notifications": True
            }
        }
        result = db.users.insert_one(user_document)
        return result.inserted_id
    except: return None

def get_user_by_email(db, email):
    return db.users.find_one({"email": email})

def get_user_by_id(db, user_id):
    try: return db.users.find_one({"_id": ObjectId(user_id)})
    except: return None

def check_user_password(user_doc, password):
    if user_doc and password:
        hp = user_doc.get("hashed_password")
        if hp: return bcrypt.checkpw(password.encode('utf-8'), hp)
    return False

def update_user_profile(db, user_id, display_name, status_message):
    try:
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"profile.display_name": display_name, "profile.bio": status_message}})
        return True
    except: return False

def update_profile_picture(db, user_id, image_data, content_type):
    try:
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"profile.profile_pic.data": Binary(image_data), "profile.profile_pic.content_type": content_type}})
        return True
    except: return False

def update_user_xp_and_level(db, user_id, new_xp, new_level):
    try:
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"profile.xp": new_xp, "profile.level": new_level}})
        return True
    except: return False

# --- Chat History ---

def get_chat_history(db, user_id, companion_id=None):
    query = {"user_id": ObjectId(user_id)}
    if companion_id == 'all':
        pass # Fetch everything
    elif companion_id == 'coder': query["companion_id"] = "coder"
    elif companion_id == 'coach': query["companion_id"] = "coach"
    else: query["$or"] = [{"companion_id": "luvisa"}, {"companion_id": {"$exists": False}}]
    return list(db.chats.find(query, {"_id": 0}).sort("timestamp", 1))

def add_message_to_history(db, user_id, sender, message, timestamp, **kwargs):
    try:
        doc = {"user_id": ObjectId(user_id), "sender": sender, "message": message, "timestamp": timestamp}
        doc.update(kwargs)
        db.chats.insert_one(doc)
        return True
    except: return False

def delete_chat_history(db, user_id):
    try:
        db.chats.delete_many({"user_id": ObjectId(user_id)})
        return True
    except: return False

# --- Journal ---

def get_journal_entry(db, user_id, date_str):
    user = db.users.find_one({"_id": ObjectId(user_id), "profile.journal_entries.date": date_str}, {"profile.journal_entries.$": 1})
    return user["profile"]["journal_entries"][0] if user and "profile" in user else None

def save_journal_entry(db, user_id, date_str, content, unlocked=False):
    entry = {"date": date_str, "content": content, "unlocked": unlocked}
    db.users.update_one({"_id": ObjectId(user_id)}, {"$push": {"profile.journal_entries": entry}})

def unlock_journal_entry(db, user_id, date_str):
    db.users.update_one({"_id": ObjectId(user_id), "profile.journal_entries.date": date_str}, {"$set": {"profile.journal_entries.$.unlocked": True}})

# ==========================================
# --- ADMIN FUNCTIONS (SEPARATE COLLECTION) ---
# ==========================================

def ensure_admin(db, email, password):
    """Creates an admin in the 'admins' collection if they don't exist."""
    # Check 'admins' collection, NOT 'users'
    if not db.admins.find_one({"email": email}):
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db.admins.insert_one({
            "email": email,
            "hashed_password": hashed,
            "role": "superadmin",
            "created_at": datetime.utcnow()
        })
        print(f"✅ Admin account created in 'admins' collection: {email}")

def verify_admin_credentials(db, email, password):
    """Verifies login against 'admins' collection."""
    admin = db.admins.find_one({"email": email})
    if admin:
        hp = admin.get("hashed_password")
        if hp: return bcrypt.checkpw(password.encode('utf-8'), hp)
    return False

# --- Admin Management Tools ---

def create_new_admin(db, email, password):
    """Force creates/updates an admin in the 'admins' collection."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Check if exists to update or insert
    existing = db.admins.find_one({"email": email})
    if existing:
        db.admins.update_one({"email": email}, {"$set": {"hashed_password": hashed}})
        print(f"✅ Updated existing admin password for: {email}")
    else:
        db.admins.insert_one({
            "email": email,
            "hashed_password": hashed,
            "role": "admin",
            "created_at": datetime.utcnow()
        })
        print(f"✅ Created new admin: {email}")

def promote_user_to_admin(db, user_id):
    """Promotes a standard user to admin using their existing credentials."""
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user: return False
        
        email = user["email"]
        if db.admins.find_one({"email": email}): return True # Already admin
        
        # Copy credentials to admin collection
        db.admins.insert_one({
            "email": email,
            "hashed_password": user["hashed_password"],
            "role": "admin",
            "created_at": datetime.utcnow()
        })
        return True
    except: return False

def delete_admin(db, email):
    """Removes an admin from the 'admins' collection."""
    result = db.admins.delete_one({"email": email})
    return result.deleted_count > 0

def get_all_admins(db):
    mins = db.admins.find({}, {"email": 1, "role": 1, "created_at": 1, "_id": 0})
    return [{"email": m["email"], "role": m.get("role", "admin"), "created_at": m.get("created_at", datetime.utcnow()).strftime("%Y-%m-%d")} for m in mins]

# --- Dashboard Data ---

def log_admin_action(db, admin_email, action, details):
    """Logs admin actions for audit."""
    try:
        db.admin_logs.insert_one({
            "admin": admin_email,
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow()
        })
    except: pass

def get_system_stats(db):
    try:
        user_count = db.users.count_documents({})
        chat_count = db.chats.count_documents({})
        pipeline = [{"$group": {"_id": None, "total_xp": {"$sum": "$profile.xp"}}}]
        xp_res = list(db.users.aggregate(pipeline))
        total_xp = xp_res[0]['total_xp'] if xp_res else 0
        maintenance = is_maintenance_active(db)
        return {"users": user_count, "messages": chat_count, "maintenance": maintenance, "total_xp": total_xp}
    except: return {}

def get_daily_signups(db):
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=6)
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        results = list(db.users.aggregate(pipeline))
        labels = []
        data = []
        date_map = {r['_id']: r['count'] for r in results}
        for i in range(7):
            d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            labels.append(d)
            data.append(date_map.get(d, 0))
        return {"labels": labels, "data": data}
    except: return {"labels": [], "data": []}

def get_all_users_admin(db, limit=100):
    cursor = db.users.find({}, {"email": 1, "profile": 1, "created_at": 1, "is_banned": 1}).sort("created_at", -1).limit(limit)
    users = []
    for u in cursor:
        users.append({
            "id": str(u["_id"]),
            "email": u["email"],
            "name": u.get("profile", {}).get("display_name", "User"),
            "level": u.get("profile", {}).get("level", 1),
            "friend_id": u.get("profile", {}).get("friend_id", "-"),
            "subscription": "free",
            "xp": u.get("profile", {}).get("xp", 0),
            "joined": u.get("created_at", datetime.utcnow()).strftime("%Y-%m-%d"),
            "is_banned": u.get("is_banned", False)
        })
    return users

def delete_user_complete(db, user_id):
    try:
        uid = ObjectId(user_id)
        db.users.delete_one({"_id": uid})
        db.chats.delete_many({"user_id": uid})
        return True
    except: return False

def toggle_user_ban(db, user_id):
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        new_status = not user.get("is_banned", False)
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_banned": new_status}})
        return new_status
    except: return None

def broadcast_notification(db, message, filters=None):
    try:
        notif = {"message": message, "iconClass": "bx-broadcast", "timestamp": datetime.utcnow()}
        result = db.users.update_many({}, {"$push": {"profile.notifications": notif}, "$set": {"profile.has_seen_notifications": False}})
        return result.modified_count
    except: return 0

def is_maintenance_active(db):
    try:
        config = db.system_config.find_one({"_id": "maintenance"})
        return config.get("active", False) if config else False
    except: return False

def set_maintenance_mode(db, active):
    try:
        db.system_config.update_one({"_id": "maintenance"}, {"$set": {"active": active}}, upsert=True)
    except: pass

def get_admin_logs(db, limit=50):
    try:
        cursor = db.admin_logs.find().sort("timestamp", -1).limit(limit)
        return [{"time": l["timestamp"].strftime("%Y-%m-%d %H:%M"), "admin": l["admin"], "action": l["action"], "details": l["details"]} for l in cursor]
    except: return []

def search_chat_messages(db, query):
    try:
        cursor = db.chats.find({"message": {"$regex": query, "$options": "i"}}).sort("timestamp", -1).limit(20)
        results = []
        for m in cursor:
            user = db.users.find_one({"_id": m["user_id"]})
            email = user["email"] if user else "Unknown"
            results.append({
                "time": m["timestamp"].strftime("%Y-%m-%d %H:%M"),
                "sender": m["sender"],
                "email": email,
                "message": m["message"]
            })
        return results
    except: return []

def delete_old_messages(db, days=7):
    """Deletes messages older than the specified number of days."""
    try:
        from datetime import datetime, timedelta, timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        result = db.chats.delete_many({"timestamp": {"$lt": cutoff_date}})
        print(f"🧹 Cleanup: Deleted {result.deleted_count} messages older than {days} days.")
        return result.deleted_count
    except Exception as e:
        print(f"❌ Cleanup Error: {e}")
        return 0

def get_flagged_messages(db): return []
def get_all_feedback(db): return []

def generate_users_csv(db):
    import csv
    from io import StringIO
    users = db.users.find()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Email', 'Name', 'Level', 'XP', 'Created At'])
    for u in users:
        writer.writerow([str(u['_id']), u.get('email', ''), u.get('profile', {}).get('display_name', ''), u.get('profile', {}).get('level', 1), u.get('profile', {}).get('xp', 0), u.get('created_at', '')])
    return output.getvalue()

def admin_update_user(db, user_id, name, xp, level, sub, password=None):
    try:
        new_level = int(level)
        new_xp = int(xp)
        
        # Auto-adjust XP if it doesn't match the requested level
        min_xp_needed = 0
        if new_level == 2: min_xp_needed = 50
        elif new_level == 3: min_xp_needed = 150
        elif new_level == 4: min_xp_needed = 300
        elif new_level == 5: min_xp_needed = 500
        elif new_level > 5: min_xp_needed = 800 + (new_level - 5) * 500
        
        if new_xp < min_xp_needed:
            new_xp = min_xp_needed

        update_data = {"profile.display_name": name, "profile.xp": new_xp, "profile.level": new_level, "subscription": sub}
        if password:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            update_data["hashed_password"] = hashed
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        return True
    except: return False