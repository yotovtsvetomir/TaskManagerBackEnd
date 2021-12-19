from rest_framework import permissions
from TaskManagerApp.models import Customer

class IsCustomer(permissions.BasePermission):
    
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        elif request.user.is_authenticated:
            if Customer.objects.filter(user=request.user).exists():
                return True
            else:
                return False
        else:
            return False
