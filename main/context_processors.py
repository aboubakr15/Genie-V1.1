from .models import Notification


def unread_notifications(request):
    """Returns the unread notification count for the authenticated user."""
    unread_notifications_count = 0
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(receiver=request.user, read=False).count()
    
    return {
        'unread_notifications_count': unread_notifications_count
    }
