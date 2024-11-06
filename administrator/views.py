from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import Group, User
from django.contrib import messages
from main.models import (LeadEmails, Sheet, ReadyShow, Log, LeadTerminationHistory, FilterWords, Referral,
                        Notification, LeadTerminationCode, SalesShow, IncomingsCount)
from main.custom_decorators import is_in_group
from .forms import UserCreationFormWithRole, UserUpdateForm
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.db import models 
from django.db.models import Q, Count, Sum
import os, logging
from datetime import datetime

logger = logging.getLogger('custom')


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def index(request):
    # Get date filter from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Convert to datetime objects if provided
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = None  # Default to None if not provided

    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d') + timezone.timedelta(days=1)  # Include end date
    else:
        end_date = None  # Default to None if not provided

    # Prospects Generated
    prospects_generated = LeadTerminationCode.objects.filter(
        flag__name__in=['PR', 'CB']
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Incomings
    '''''
    This model is used to count the incomings that have been made since the start of operating on the App,
    so it does not change at the dashboard if the termination code was changed.
    ''''' 
    incomings = IncomingsCount.objects.filter(date__range=(start_date, end_date)).count()

    # Flags
    total_flags = LeadTerminationCode.objects.filter(
        flag__name='FL'
    ).filter(entry_date__range=(start_date, end_date)).count()

    flags_qualified = LeadTerminationCode.objects.filter(
        flag__name='FL',
        is_qualified=True
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Avg. #Calls
    avg_calls = SalesShow.objects.filter(
        is_done=True
    ).filter(done_date__range=(start_date, end_date)).aggregate(total_leads=Count('leads'))['total_leads'] or 0

    # CD Count
    cd_count = LeadTerminationCode.objects.filter(
        flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Total #Nights
    total_nights = LeadTerminationCode.objects.filter(
        flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).aggregate(total_nights=Sum('num_nights'))['total_nights'] or 0

    return render(request, "sales_manager/index.html", {
        "prospects_generated": prospects_generated,
        "incomings": incomings,
        "total_flags": total_flags,
        "flags_qualified": flags_qualified,
        "avg_calls": avg_calls,
        "cd_count": cd_count,
        "total_nights": total_nights,
        "start_date": start_date.strftime('%Y-%m-%d') if start_date else '',
        "end_date": end_date.strftime('%Y-%m-%d') if end_date else '',
    })


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def add_user(request):
    if request.method == 'POST':
        form = UserCreationFormWithRole(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1']) 
            role = form.cleaned_data['role']

            group, created = Group.objects.get_or_create(name=role)
            user.save()
            user.groups.add(group)

            messages.success(request, 'User created successfully.')
            return redirect('administrator:add-user')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = UserCreationFormWithRole()

    return render(request, 'administrator/add_user.html', {'form': form})


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def manage_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(Q(username__icontains=query))
    
    # Pagination
    paginator = Paginator(users, 10)  # Show 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "administrator/manage_users.html", {
        'page_obj': page_obj,
    'query': query,
    })


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('administrator:manage-users')
    return render(request, 'administrator/confirm_delete.html', {'user': user})


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            new_password = form.cleaned_data.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            role = form.cleaned_data.get('role')
            group, created = Group.objects.get_or_create(name=role)
            user.groups.clear()
            user.groups.add(group)

            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('administrator:manage-users')
    else:
        form = UserUpdateForm(instance=user)

    return render(request, 'administrator/edit_user.html', {'form': form})


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def view_logs(request):
    query = request.GET.get('q', '')  # Get the search query from the request
    logs = Log.objects.all().order_by('-date')

    if query:
        logs = logs.filter(Q(message__icontains=query))

    paginator = Paginator(logs, 30)
    page_num = request.GET.get('page')
    page_obj = paginator.get_page(page_num)

    context = {
        'logs': page_obj,
        'query': query  # Pass the query back to the template
    }

    return render(request, "administrator/view_logs.html", context)


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def manage_sheets(request):
    sheets = Sheet.objects.filter(is_approved=True, is_done=False).order_by("-id")
    q = request.GET.get("q", '')

    if q:
        sheets = sheets.filter(
            Q(name__icontains=q)
        )
    paginator=Paginator(sheets, 50)


    page_num = request.GET.get("page", '')
    page_obj = paginator.get_page(page_num)

    sheets = sheets.annotate(leads_count=models.Count('leads'))

    context = {
        "page_obj":page_obj,
        "q":q
    }


    return render(request, "administrator/manage_sheets.html", context)


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def cut_sheet_into_ready_show(request, sheet_id):
    # Get the sheet and mark it as done
    sheet = get_object_or_404(Sheet, id=sheet_id)
    sheet.is_done = True
    sheet.done_date = timezone.now()
    sheet.save()

    # Filter out leads with termination codes 'show' and 'CD'
    leads_to_referral = []
    filtered_leads_by_zone = {'cen': [], 'est': [], 'pac': []}

    # Group the leads by time zone (cen, est, pac)
    time_zones = ['cen', 'est', 'pac']
    for tz in time_zones:
        leads = sheet.leads.filter(time_zone=tz)
        for lead in leads:
            if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name='show').exists():
                continue  # Skip leads with termination code 'show'
            if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name='CD').exists():
                leads_to_referral.append(lead)  # Add to referral list
                continue  # Skip leads with termination code 'CD'
            filtered_leads_by_zone[tz].append(lead)  # Keep leads that can be assigned

    # Create 3 ReadyShow objects
    labels = ['EHUB', 'EHUB2', 'EP']
    ready_show_objects = [ReadyShow.objects.create(sheet=sheet, label=labels[i]) for i in range(3)]

    # Distribute leads from each time zone to each ReadyShow object evenly
    for tz, leads in filtered_leads_by_zone.items():
        total_leads = len(leads)
        split_size = total_leads // 3  # Calculate the regular size for each group

        # Split leads evenly among the 3 ReadyShow objects
        for i in range(3):
            start_index = i * split_size
            end_index = start_index + split_size
            ready_show_leads = leads[start_index:end_index]
            ready_show_objects[i].leads.add(*ready_show_leads)

        # Handle leftover leads (if any)
        leftover_leads = leads[3 * split_size:]
        for i, lead in enumerate(leftover_leads):
            ready_show_objects[i % 3].leads.add(lead)

    # Create a new workbook and select the active sheet
    workbook = openpyxl.Workbook()
    sheet_ws = workbook.active
    sheet_ws.title = "Leads"

    # Set the headers
    sheet_ws.append(["Company Name", "Email"])

    # Collect all leads for the email sheet, skipping leads with termination code 'show' and 'CD'
    all_leads = sheet.leads.all()
    for lead in all_leads:
        # Skip leads with a termination code 'show' or 'CD'
        if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name__in=['show', 'CD']).exists():
            continue

        # Skip leads whose name is in FilterWords with filter type 'email'
        if FilterWords.objects.filter(word=lead.name, filter_types__name='email').exists():
            continue

        # Fetch the associated email from LeadEmails model
        lead_email_obj = LeadEmails.objects.filter(lead=lead, sheet=sheet).first()

        # Only append the lead to the Excel file if it has an email
        if lead_email_obj:
            lead_email = lead_email_obj.value
            sheet_ws.append([lead.name, lead_email])

    # Add leads with termination code 'CD' to the Referral model
    for lead in leads_to_referral:
        Referral.objects.create(lead=lead, sheet=sheet)
        
        # Attempt to send notification to the user
        try:
            # Get the operations_manager group
            operations_manager_group = Group.objects.get(name="operations_manager")
            # Get all users in the operations_manager group
            operations_managers = operations_manager_group.user_set.all()

            # Send a notification to each user in the operations_manager group
            for user in operations_managers:
                Notification.objects.create(
                    sender=user,  # it’s a system notification
                    receiver=user,
                    message=f"Lead '{lead.name}' detected in show '{sheet.name}' as a former Closed Deal, Please check the Referrals sheet.",
                    notification_type=6   # Referral
                )

        except Exception as e:
            logger.error(f"Failed to create notification for user {user.username}: {e}")

    # Define the hardcoded save path for the Excel file
    save_path = os.path.join("F:\Projects\IBH\DataBase-Project\emails", f"{sheet.name}")

    # Save the Excel workbook to the specified path
    workbook.save(save_path)

    return redirect('administrator:manage-sheets')


def cut_multiple_sheets(request):
    if request.method == "POST":
        selected_sheets = request.POST.getlist('selected_sheets')
        for sheet_id in selected_sheets:
            # Call your `cut_sheet_into_ready_show` function for each selected sheet
            cut_sheet_into_ready_show(request, sheet_id)

    return redirect('administrator:manage-sheets')


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def done_sheets(request):
    # Fetch sheets that are marked as done
    done_sheets_list = Sheet.objects.filter(is_done=True).order_by("-id")
    
    # Set up pagination (10 items per page, for example)
    paginator = Paginator(done_sheets_list, 30)  # Show 10 sheets per page
    page_number = request.GET.get('page')
    done_sheets = paginator.get_page(page_number)

    context = {
        'done_sheets': done_sheets
    }
    return render(request, 'administrator/done_sheets.html', context)