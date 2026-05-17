"""
Role-based access control (RBAC) utilities
"""
from enum import Enum
from typing import List


class UserRole(str, Enum):
    """User roles in the system"""
    USER = "user"                    # Regular customer
    PROVIDER = "provider"            # Service provider
    ADMIN = "admin"                  # System administrator
    SUPER_ADMIN = "super_admin"      # Super administrator


class Permission(str, Enum):
    """System permissions"""
    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Provider permissions
    PROVIDER_READ = "provider:read"
    PROVIDER_WRITE = "provider:write"
    PROVIDER_DELETE = "provider:delete"
    
    # Booking permissions
    BOOKING_CREATE = "booking:create"
    BOOKING_READ = "booking:read"
    BOOKING_UPDATE = "booking:update"
    BOOKING_CANCEL = "booking:cancel"
    
    # Admin permissions
    ADMIN_ACCESS = "admin:access"
    ANALYTICS_READ = "analytics:read"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserRole, List[Permission]] = {
    UserRole.USER: [
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.BOOKING_CREATE,
        Permission.BOOKING_READ,
        Permission.BOOKING_CANCEL,
    ],
    UserRole.PROVIDER: [
        Permission.PROVIDER_READ,
        Permission.PROVIDER_WRITE,
        Permission.BOOKING_READ,
        Permission.BOOKING_UPDATE,
    ],
    UserRole.ADMIN: [
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.PROVIDER_READ,
        Permission.PROVIDER_WRITE,
        Permission.BOOKING_READ,
        Permission.BOOKING_UPDATE,
        Permission.ADMIN_ACCESS,
        Permission.ANALYTICS_READ,
    ],
    UserRole.SUPER_ADMIN: list(Permission),  # All permissions
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """
    Check if role has specific permission
    
    Args:
        role: User role
        permission: Permission to check
    
    Returns:
        True if role has permission
    """
    return permission in ROLE_PERMISSIONS.get(role, [])


def get_role_permissions(role: UserRole) -> List[Permission]:
    """
    Get all permissions for a role
    
    Args:
        role: User role
    
    Returns:
        List of permissions
    """
    return ROLE_PERMISSIONS.get(role, [])