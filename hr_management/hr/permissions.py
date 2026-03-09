from rest_framework import permissions

class IsHRorAdmin(permissions.BasePermission):
    """
    Only allow HR Managers or Admins to see salary-related data.
    """
    def has_permission(self, request, view):
        # 1. Check if the user is even logged in
        if not request.user or not request.user.is_authenticated:
            return False
            
        # 2. Check their role
        return request.user.role in ['HR', 'ADMIN']