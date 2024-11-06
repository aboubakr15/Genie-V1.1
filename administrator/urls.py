from django.urls import path
from .views import (add_user , delete_user, edit_user, index, done_sheets,
    manage_users, view_logs, cut_sheet_into_ready_show, manage_sheets, cut_multiple_sheets)

app_name="administrator"
urlpatterns = [
    path('', index, name='administrator_index'),
    path('users/add-user/', add_user, name='add-user'),
    path('users/manage-users/', manage_users, name='manage-users'),
    path('view-logs/', view_logs, name='view-logs'),
    path('users/delete-user/<int:user_id>/', delete_user, name='delete-user'),
    path('users/edit-user/<int:user_id>/', edit_user, name='edit-user'),
    path('manage-sheets/', manage_sheets, name='manage-sheets'),
    path('cut-sheet/<int:sheet_id>/', cut_sheet_into_ready_show, name='cut-sheet'),
    path('sheets-done/', done_sheets, name='sheets-done'),
    path('cut-multiple-sheets/', cut_multiple_sheets, name='cut-multiple-sheets'),
]
