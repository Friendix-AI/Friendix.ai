import database
import os

def main():
    print("--- Friendix Admin Manager (Separate Collection) ---")
    
    # 1. Connect to Database
    try:
        database.load_config()
        db = database.get_db()
        if db is None:
            print("🔥 Error: Could not connect to MongoDB.")
            return
        print("✅ Connected to Database.")
    except Exception as e:
        print(f"🔥 Connection Error: {e}")
        return

    while True:
        print("\n--- ADMINS COLLECTION MENU ---")
        print("1. Create/Update Admin (In 'admins' collection)")
        print("2. Delete Admin")
        print("3. List All Admins")
        print("4. Exit")
        
        choice = input("Enter choice (1-4): ")

        if choice == '1':
            email = input("Enter Admin Email: ").strip()
            password = input("Enter Admin Password: ").strip()
            
            if not email or not password:
                print("❌ Email and Password required.")
                continue
                
            database.create_new_admin(db, email, password)

        elif choice == '2':
            email = input("Enter Admin Email to DELETE: ").strip()
            if database.delete_admin(db, email):
                print(f"✅ Deleted admin: {email}")
            else:
                print(f"❌ Admin not found.")

        elif choice == '3':
            print("\n--- Current Admins ---")
            admins = list(db.admins.find({}, {"email": 1, "role": 1, "created_at": 1}))
            if not admins:
                print("No admins found.")
            else:
                for a in admins:
                    print(f"• {a.get('email')} | Role: {a.get('role')} | Created: {a.get('created_at')}")

        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()