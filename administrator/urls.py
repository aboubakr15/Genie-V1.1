from django.urls import path
from .views import (add_user , delete_user, edit_user, index, done_sheets, archive_sheet, archived_sheets,
                     unarchive_sheet, manage_users, view_logs, cut_sheet_into_ready_show, manage_sheets,view_sheet_admin,
                     cut_multiple_sheets, manage_x_sheets, cut_x_multiple_sheets, done_x_sheets, archive_sheet_bulk)

app_name="administrator"
urlpatterns = [
    path('', index, name='administrator_index'),
    path('users/add-user/', add_user, name='add-user'),
    path('users/manage-users/', manage_users, name='manage-users'),
    path('view-logs/', view_logs, name='view-logs'),
    path('users/delete-user/<int:user_id>/', delete_user, name='delete-user'),
    path('users/edit-user/<int:user_id>/', edit_user, name='edit-user'),
    path('manage-sheets/', manage_sheets, name='manage-sheets'),
    path('manage-x-sheets/', manage_x_sheets, name='manage-x-sheets'),
    path('cut-sheet/<int:sheet_id>/', cut_sheet_into_ready_show, name='cut-sheet'),
    path('sheets-done/', done_sheets, name='sheets-done'),
    path('sheets-x-done/', done_x_sheets, name='sheets-x-done'),
    path('cut-multiple-sheets/', cut_multiple_sheets, name='cut-multiple-sheets'),
    path('cut-multiple-x-sheets/', cut_x_multiple_sheets, name='cut-multiple-x-sheets'),
    path('archive-sheet/<int:sheet_id>/', archive_sheet, name='archive-sheet'),
    path('archive-sheet-bulk/', archive_sheet_bulk, name='archive-sheet-bulk'),
    path('archived-sheets/', archived_sheets, name='archived-sheets'),
    path('unarchive-sheet/<int:sheet_id>/', unarchive_sheet, name='unarchive-sheet'),
    path('administrator/sheet/<int:sheet_id>/', view_sheet_admin, name='view-sheet'),
]
