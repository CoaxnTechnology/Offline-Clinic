#!/usr/bin/env python3
"""
Initialize default admin users for the clinic system.
Run with: uv run python3 init_admin.py
"""
from app import create_app
from app.extensions import db
from app.models import Admin

# Default admin users to create
DEFAULT_ADMINS = [
    {
        'username': 'admin',
        'email': 'admin@clinic.com',
        'password': 'admin123',
        'first_name': 'Super',
        'last_name': 'Admin',
        'role': 'doctor',  # Default role
        'phone': ''
    },
    {
        'username': 'doctor1',
        'email': 'doctor1@clinic.com',
        'password': 'doctor123',
        'first_name': 'John',
        'last_name': 'Doctor',
        'role': 'doctor',
        'phone': ''
    },
    {
        'username': 'technician1',
        'email': 'technician1@clinic.com',
        'password': 'tech123',
        'first_name': 'Jane',
        'last_name': 'Technician',
        'role': 'technician',
        'phone': ''
    },
    {
        'username': 'receptionist1',
        'email': 'receptionist1@clinic.com',
        'password': 'recep123',
        'first_name': 'Bob',
        'last_name': 'Receptionist',
        'role': 'receptionist',
        'phone': ''
    }
]

def create_admins():
    """Create default admin users"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Initializing Admin Users")
        print("=" * 60)
        print()
        
        created_count = 0
        
        for admin_data in DEFAULT_ADMINS:
            username = admin_data['username']
            
            # Check if admin already exists
            existing = Admin.query.filter_by(username=username).first()
            if existing:
                print(f"  - Admin '{username}' already exists (skipping)")
                continue
            
            # Create admin
            admin = Admin(
                username=username,
                email=admin_data['email'],
                first_name=admin_data['first_name'],
                last_name=admin_data['last_name'],
                role=admin_data['role'],
                phone=admin_data.get('phone', ''),
                is_active=True
            )
            admin.set_password(admin_data['password'])
            
            db.session.add(admin)
            created_count += 1
            print(f"  ✓ Created: {username} ({admin_data['role']}) - Password: {admin_data['password']}")
        
        db.session.commit()
        
        print()
        print("=" * 60)
        print(f"✅ Created {created_count} new admin user(s)")
        print("=" * 60)
        print("\n⚠️  IMPORTANT: Change passwords after first login!")
        print("\nAvailable Roles:")
        print("  - doctor")
        print("  - technician")
        print("  - receptionist")

if __name__ == '__main__':
    create_admins()
