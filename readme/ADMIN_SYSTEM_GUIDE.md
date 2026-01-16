# Admin System Guide - Roles and Permissions

## Overview

The clinic backend now includes a comprehensive **Role-Based Access Control (RBAC)** system that manages user authentication, roles, and permissions.

## Database Schema

### Tables Created

1. **`users`** - User accounts
2. **`roles`** - User roles (Admin, Doctor, Receptionist, etc.)
3. **`permissions`** - Individual permissions (e.g., `patient.create`, `dicom.view`)
4. **`user_roles`** - Many-to-many relationship between users and roles
5. **`role_permissions`** - Many-to-many relationship between roles and permissions
6. **`audit_logs`** - Audit trail (already existed, now properly linked)

## Models

### User Model (`app/models/user.py`)

**Fields:**
- `id` - Primary key
- `username` - Unique username
- `email` - Unique email
- `password_hash` - Bcrypt hashed password
- `first_name`, `last_name` - Personal information
- `phone` - Contact number
- `is_active` - Account status
- `is_super_admin` - Bypass all permissions (full access)
- `last_login` - Last login timestamp
- `login_count` - Login counter
- `created_at`, `updated_at` - Timestamps

**Key Methods:**
- `set_password(password)` - Hash and set password
- `check_password(password)` - Verify password
- `has_role(role_name)` - Check if user has specific role
- `has_permission(permission_name)` - Check if user has specific permission
- `has_any_role(*role_names)` - Check if user has any of the roles
- `has_all_roles(*role_names)` - Check if user has all roles
- `get_permissions()` - Get all user permissions
- `add_role(role)` - Add role to user
- `remove_role(role)` - Remove role from user

### Role Model (`app/models/role.py`)

**Fields:**
- `id` - Primary key
- `name` - Unique role name
- `description` - Role description
- `is_active` - Role status
- `created_at`, `updated_at` - Timestamps

**Key Methods:**
- `add_permission(permission)` - Add permission to role
- `remove_permission(permission)` - Remove permission from role
- `has_permission(permission_name)` - Check if role has permission

### Permission Model (`app/models/permission.py`)

**Fields:**
- `id` - Primary key
- `name` - Unique permission name (format: `resource.action`)
- `description` - Permission description
- `resource` - Resource type (patient, appointment, dicom, etc.)
- `action` - Action type (create, read, update, delete, etc.)
- `is_active` - Permission status
- `created_at`, `updated_at` - Timestamps

**Permission Naming Convention:**
- Format: `{resource}.{action}`
- Examples: `patient.create`, `dicom.view`, `report.finalize`

## Default Roles

The system comes with **3 default roles**:

1. **Doctor**
   - Clinical access
   - View patients and appointments
   - View and download DICOM images
   - Create, update, and finalize reports
   - **Permissions**: patient.read, patient.search, appointment.read, appointment.update, dicom.view, dicom.download, report.create, report.read, report.update, report.finalize

2. **Technician**
   - Technical operations
   - View patients and appointments
   - Receive DICOM images
   - Send MWL to machines
   - **Permissions**: patient.read, patient.search, appointment.read, appointment.update, dicom.view, dicom.receive, dicom.mwl_send

3. **Receptionist**
   - Front desk operations
   - Create and manage patients
   - Create and schedule appointments
   - Send MWL to machines
   - **Permissions**: patient.create, patient.read, patient.update, patient.search, appointment.create, appointment.read, appointment.update, appointment.schedule, dicom.mwl_send

### Super Admin User

A super admin user is created separately (not a role). Users with `is_super_admin=True` flag have full system access and bypass all permission checks. This is useful for system administrators.

## Default Permissions

Permissions are organized by resource:

### Patient Permissions
- `patient.create` - Create new patients
- `patient.read` - View patient information
- `patient.update` - Update patient information
- `patient.delete` - Delete patients
- `patient.search` - Search patients

### Appointment Permissions
- `appointment.create` - Create appointments
- `appointment.read` - View appointments
- `appointment.update` - Update appointments
- `appointment.delete` - Delete appointments
- `appointment.schedule` - Schedule appointments

### DICOM Permissions
- `dicom.view` - View DICOM images
- `dicom.download` - Download DICOM files
- `dicom.delete` - Delete DICOM studies
- `dicom.mwl_send` - Send MWL to machines
- `dicom.receive` - Receive DICOM images

### Report Permissions
- `report.create` - Create reports
- `report.read` - View reports
- `report.update` - Update reports
- `report.delete` - Delete reports
- `report.finalize` - Finalize reports

### User Permissions
- `user.create` - Create users
- `user.read` - View users
- `user.update` - Update users
- `user.delete` - Delete users
- `user.manage_roles` - Manage user roles

### Admin Permissions
- `admin.access` - Access admin panel
- `admin.manage_settings` - Manage system settings
- `admin.view_logs` - View audit logs
- `admin.export_data` - Export data

## Setup Instructions

### Step 1: Apply Database Migration

```bash
export FLASK_APP=run.py
uv run flask db upgrade
```

### Step 2: Initialize Default Roles and Permissions

```bash
export FLASK_APP=run.py
uv run python3 init_roles_permissions.py
```

This will:
- Create all default permissions
- Create all default roles
- Assign permissions to roles
- Create a default super admin user

**Default Super Admin Credentials:**
- Username: `admin`
- Password: `admin123`
- **⚠️ Change password after first login!**
- Note: Super admin uses `is_super_admin=True` flag (not a role)

### Step 3: Verify Setup

Check that tables were created:

```bash
psql -U clinic_db -h localhost -d clinic_db -c "\dt"
```

You should see:
- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `audit_logs`

## Usage Examples

### Creating a User

```python
from app import create_app
from app.models import User, Role

app = create_app()
with app.app_context():
    # Create user
    user = User(
        username='doctor1',
        email='doctor1@clinic.com',
        first_name='John',
        last_name='Doe',
        is_active=True
    )
    user.set_password('secure_password')
    
    # Assign role
    doctor_role = Role.query.filter_by(name='Doctor').first()
    user.add_role(doctor_role)
    
    db.session.add(user)
    db.session.commit()
```

### Checking Permissions

```python
# Check if user has permission
if current_user.has_permission('patient.create'):
    # Allow creating patient
    pass

# Check if user has role
if current_user.has_role('Doctor'):
    # Doctor-specific logic
    pass

# Check multiple roles
if current_user.has_any_role('Doctor', 'Radiologist'):
    # Either doctor or radiologist
    pass
```

### Adding Custom Permissions

```python
from app.models import Permission

# Create new permission
permission = Permission(
    name='patient.export',
    description='Export patient data',
    resource='patient',
    action='export',
    is_active=True
)
db.session.add(permission)
db.session.commit()
```

### Creating Custom Role

```python
from app.models import Role, Permission

# Create role
custom_role = Role(
    name='Lab Technician',
    description='Laboratory technician role',
    is_active=True
)

# Add permissions
view_perm = Permission.query.filter_by(name='patient.read').first()
create_perm = Permission.query.filter_by(name='report.create').first()

custom_role.add_permission(view_perm)
custom_role.add_permission(create_perm)

db.session.add(custom_role)
db.session.commit()
```

## Integration with Flask-Login

To use with Flask-Login (for web authentication):

```python
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Protect routes
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.has_permission('admin.access'):
        return "Access denied", 403
    return "Admin panel"
```

## Permission Decorator Example

Create a custom decorator for permission checks:

```python
from functools import wraps
from flask import abort

def require_permission(permission_name):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage
@app.route('/patients/create')
@require_permission('patient.create')
def create_patient():
    # Only users with patient.create permission can access
    pass
```

## Audit Logging

The `AuditLog` model is now properly linked to users:

```python
from app.models import AuditLog

# Log an action
log = AuditLog(
    user_id=current_user.id,
    action='Patient Created',
    entity_type='Patient',
    entity_id=patient.id,
    details='Created new patient record'
)
db.session.add(log)
db.session.commit()
```

## Security Best Practices

1. **Password Security**
   - Always use `set_password()` method (uses bcrypt)
   - Never store plain text passwords
   - Enforce password complexity rules

2. **Super Admin**
   - Limit super admin accounts
   - Use super admin only for system administration
   - Regular users should have specific roles

3. **Permission Checks**
   - Always check permissions before sensitive operations
   - Don't rely only on UI hiding buttons
   - Check permissions on both frontend and backend

4. **Role Management**
   - Assign minimum required permissions
   - Review roles periodically
   - Deactivate unused roles/permissions

5. **Audit Logging**
   - Log all sensitive operations
   - Track permission changes
   - Monitor failed access attempts

## Troubleshooting

### Issue: "User has no roles"
**Solution**: Assign roles using `user.add_role(role)`

### Issue: "Permission not found"
**Solution**: Check permission name format (`resource.action`)

### Issue: "Super admin not working"
**Solution**: Ensure `is_super_admin=True` is set

### Issue: "Can't login"
**Solution**: 
- Check password hash is set correctly
- Use `user.set_password()` method
- Verify `is_active=True`

## Next Steps

1. **Integrate with Flask-Login** for web authentication
2. **Create admin routes** for user/role management
3. **Add permission checks** to existing routes
4. **Create admin UI** for managing users and roles
5. **Add password reset** functionality
6. **Implement session management**

## Files Created

- `app/models/user.py` - User model
- `app/models/role.py` - Role model
- `app/models/permission.py` - Permission model
- `init_roles_permissions.py` - Initialization script
- Migration file in `migrations/versions/`

## Summary

The admin system provides:
- ✅ User management with authentication
- ✅ Role-based access control
- ✅ Granular permissions
- ✅ Super admin bypass
- ✅ Audit logging integration
- ✅ Easy permission checking
- ✅ Flexible role assignment

Ready to use for securing your clinic backend!
