from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import Group, User
from django.contrib import messages
from main.models import (LeadEmails, Sheet, ReadyShow, Log, LeadTerminationHistory, FilterWords, Referral,
                        LeadTerminationCode, SalesShow, IncomingsCount, LeadsColors)
from main.custom_decorators import is_in_group
from .forms import UserCreationFormWithRole, UserUpdateForm
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.db import models 
from django.db.models import Q, Count, Sum
import os, logging, openpyxl
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
    sheets = Sheet.objects.filter(is_approved=True, is_done=False, is_archived=False, is_x=False).order_by("-id")
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
def manage_x_sheets(request):
    sheets = Sheet.objects.filter(is_approved=True, is_done=False, is_archived=False, is_x=True).order_by("-id")
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


    return render(request, "administrator/manage_x_sheets.html", context)


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def cut_sheet_into_ready_show(request, sheet_id):
    # Get the sheet and mark it as done
    sheet = get_object_or_404(Sheet, id=sheet_id)
    sheet.is_done = True
    sheet.done_date = timezone.now()
    sheet.save()

    # Define country sets
    uk_countries = {'scotland', 'wales', 'england', 'ireland', 'uk'}

    europe_countries = {
        'poland', 'france', 'lithuania', 'sweden', 'spain', 'russia', 'austria',
        'czechia', 'belarus', 'latvia', 'malta', 'greece', 'andorra', 'moldova',
        'turkiye', 'georgia', 'germany', 'bulgaria', 'norway', 'romania',
        'estonia', 'san marino', 'slovenia', 'switzerland', 'montenegro', 'croatia',
        'bosnia & herzegovina', 'isle of man', 'kosovo', 'luxembourg', 'hungary',
        'netherlands', 'italy', 'portugal', 'denmark', 'finland', 'ukraine',
        'north macedonia', 'lichtenstein', 'slovakia', 'belgium', 'monaco',
        'albania', 'cyprus', 'kazakhstan'
    }

    asia_countries = {
        'india', 'indonesia', 'pakistan', 'bangladesh', 'japan', 'philippines',
        'vietnam', 'iran', 'thailand', 'south korea', 'malaysia', 'saudi arabia',
        'nepal', 'sri lanka', 'cambodia', 'jordan', 'united arab emirates',
        'tajikistan', 'azerbaijan', 'israel', 'laos', 'turkmenistan', 'kyrgyzstan',
        'singapore', 'oman', 'kuwait', 'mongolia', 'qatar', 'armenia', 'bahrain',
        'maldives', 'brunei', 'hong kong', 'china'
    }

    # Initialize containers
    leads_to_referral = []
    na_leads = {'cen': [], 'est': [], 'pac': []}
    region_leads = {'UK': [], 'Europe': [], 'Asia': []}
    red_blue_na_leads = {'cen': [], 'est': [], 'pac': []}
    red_blue_region_leads = {'UK': [], 'Europe': [], 'Asia': []}

    def get_shows_count(total_leads):
        if total_leads <= 20:
            return 1
        elif total_leads <= 50:
            return 2
        elif total_leads <= 100:
            return 4
        elif total_leads <= 200:
            return 8
        else:
            return total_leads // 10

    # Process all leads
    all_leads = sheet.leads.all()
    for lead in all_leads:
        # Handle referrals
        if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name__in=['show', 'CD']).exists():
            if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name='CD').exists():
                leads_to_referral.append(lead)
            continue

        # Determine lead's region if it's not NA
        region = None
        time_zone_lower = lead.time_zone.strip().lower() if lead.time_zone else ''
        if time_zone_lower not in ['cen', 'est', 'pac']:
            if time_zone_lower in uk_countries:
                region = 'UK'
            elif time_zone_lower in europe_countries:
                region = 'Europe'
            elif time_zone_lower in asia_countries:
                region = 'Asia'

        # Sort leads based on color and region
        if sheet.is_x and LeadsColors.objects.filter(lead=lead, sheet=sheet, color__in=['red', 'blue']).exists():
            if time_zone_lower in ['cen', 'est', 'pac']:
                red_blue_na_leads[lead.time_zone.lower()].append(lead)
            elif region:
                red_blue_region_leads[region].append(lead)
        else:
            if time_zone_lower in ['cen', 'est', 'pac']:
                na_leads[lead.time_zone.lower()].append(lead)
            elif region:
                region_leads[region].append(lead)

    def distribute_na_leads_evenly(leads_dict, num_shows):
        shows_leads = [[] for _ in range(num_shows)]
        
        for zone in ['cen', 'est', 'pac']:
            leads = leads_dict[zone]
            zone_lead_count = len(leads)
            split_size = zone_lead_count // num_shows if num_shows > 0 else 0
            
            for i in range(num_shows):
                start_idx = i * split_size
                end_idx = start_idx + split_size
                shows_leads[i].extend(leads[start_idx:end_idx])
            
            # Handle leftover leads
            leftover_leads = leads[num_shows * split_size:]
            for i, lead in enumerate(leftover_leads):
                shows_leads[i % num_shows].append(lead)
        
        return shows_leads

    # Handle red/blue leads first if sheet is_x
    if sheet.is_x:
        # Process NA red/blue leads
        total_na_red_blue = sum(len(leads) for leads in red_blue_na_leads.values())
        if total_na_red_blue > 0:
            sales_shows_count = get_shows_count(total_na_red_blue)
            na_sales_show_leads = distribute_na_leads_evenly(red_blue_na_leads, sales_shows_count)
            
            for idx, leads_chunk in enumerate(na_sales_show_leads, start=1):
                sales_show = SalesShow.objects.create(
                    name=f"{sheet.name} X ({idx})",
                    sheet=sheet,
                    is_done=False,
                    is_x=True,
                    label="EHUB"  # Default label for NA sales shows
                )
                sales_show.leads.add(*leads_chunk)
                sales_show.save()

        # Process regional red/blue leads
        for region, leads in red_blue_region_leads.items():
            if leads:
                region_count = len(leads)
                shows_count = get_shows_count(region_count)
                
                # Split leads into chunks
                chunk_size = len(leads) // shows_count
                for i in range(shows_count):
                    start_idx = i * chunk_size
                    end_idx = start_idx + chunk_size if i < shows_count - 1 else len(leads)
                    
                    sales_show = SalesShow.objects.create(
                        name=f"{sheet.name} {region} ({i+1})",
                        sheet=sheet,
                        is_done=False,
                        is_x=True,
                        label=region  # Regional label for regional sales shows
                    )
                    sales_show.leads.add(*leads[start_idx:end_idx])
                    sales_show.save()

    # Create ReadyShows for remaining leads (both for X and non-X sheets)
    # First, create 3 ReadyShows for NA leads
    labels = ['EHUB', 'EHUB2', 'EP']
    na_ready_shows = [
        ReadyShow.objects.create(
            sheet=sheet,
            label=label,
            name=f"{sheet.name} - {label}",
        ) for label in labels
    ]
    
    # Distribute NA leads evenly across the 3 shows
    na_ready_show_leads = distribute_na_leads_evenly(na_leads, 3)
    for show, leads in zip(na_ready_shows, na_ready_show_leads):
        show.leads.add(*leads)
        show.save()

    # Create one ReadyShow for each region
    for region, leads in region_leads.items():
        if leads:
            ready_show = ReadyShow.objects.create(
                sheet=sheet,
                label=region,
                name=f"{sheet.name} - {region}",
            )
            ready_show.leads.add(*leads)
            ready_show.save()

    # Handle referrals
    for lead in leads_to_referral:
        Referral.objects.create(lead=lead, sheet=sheet)

    # Handle emails
    workbook = openpyxl.Workbook()
    sheet_ws = workbook.active
    sheet_ws.title = "Leads"
    sheet_ws.append(["Company Name", "Email"])
    
    if sheet.is_x:
        # For X sheets, only include red/blue leads
        email_leads = [
            lead for lead in all_leads
            if LeadsColors.objects.filter(lead=lead, sheet=sheet, color__in=['red', 'blue']).exists()
        ]
    else:
        # For non-X sheets, include all leads
        email_leads = all_leads

    for lead in email_leads:
        if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name__in=['show', 'CD']).exists():
            continue
        if FilterWords.objects.filter(word=lead.name, filter_types__name='email').exists():
            continue

        lead_email_obj = LeadEmails.objects.filter(lead=lead, sheet=sheet).first()
        if lead_email_obj:
            lead_email = lead_email_obj.value
            sheet_ws.append([lead.name, lead_email])

    # Save the Excel workbook   //IBH/Inbound/Mails
    save_path = os.path.join("C:\\Users\\MEAPAL\\Downloads", f"{sheet.name}.xlsx")
    workbook.save(save_path)

    return redirect('administrator:manage-sheets')




@user_passes_test(lambda user: is_in_group(user, "administrator"))
def cut_multiple_sheets(request):
    if request.method == "POST":
        selected_sheets = request.POST.getlist('selected_sheets')
        for sheet_id in selected_sheets:
            # Call your `cut_sheet_into_ready_show` function for each selected sheet
            cut_sheet_into_ready_show(request, sheet_id)

    return redirect('administrator:manage-sheets')


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def cut_x_multiple_sheets(request):
    if request.method == "POST":
        selected_sheets = request.POST.getlist('selected_sheets')
        for sheet_id in selected_sheets:
            # Call your `cut_sheet_into_ready_show` function for each selected sheet
            cut_sheet_into_ready_show(request, sheet_id)

    return redirect('administrator:manage-x-sheets')


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def done_sheets(request):
    # Fetch sheets that are marked as done
    done_sheets_list = Sheet.objects.filter(is_done=True, is_x=False).order_by("-id")
    
    # Set up pagination (10 items per page, for example)
    paginator = Paginator(done_sheets_list, 30)  # Show 10 sheets per page
    page_number = request.GET.get('page')
    done_sheets = paginator.get_page(page_number)

    context = {
        'done_sheets': done_sheets
    }
    return render(request, 'administrator/done_sheets.html', context)


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def done_x_sheets(request):
    # Fetch sheets that are marked as done
    done_sheets_list = Sheet.objects.filter(is_done=True, is_x=True).order_by("-id")
    
    # Set up pagination (10 items per page, for example)
    paginator = Paginator(done_sheets_list, 30)  # Show 10 sheets per page
    page_number = request.GET.get('page')
    done_sheets = paginator.get_page(page_number)

    context = {
        'done_sheets': done_sheets
    }
    return render(request, 'administrator/done_sheets.html', context)


@user_passes_test(lambda user: is_in_group(user, "administrator"))
def archive_sheet(request, sheet_id):
    if request.method == 'POST':
        sheet = get_object_or_404(Sheet, id=sheet_id)  # Fetch the sheet by ID
        sheet.is_archived = True  # Mark as archived
        sheet.save()  # Save the changes to the database
        
        # Get the referring URL or use a fallback
        referer_url = request.META.get('HTTP_REFERER', 'administrator:manage-sheets')
        
        # Redirect to the referring URL
        return HttpResponseRedirect(referer_url)
    

@user_passes_test(lambda user: is_in_group(user, "administrator"))
def archived_sheets(request):
    query = request.GET.get('q', '')  # Get search query
    archived_sheets = Sheet.objects.filter(is_archived=True).order_by('-id')

    if query:
        archived_sheets = archived_sheets.filter(name__icontains=query)  # Filter by sheet name

    # Pagination
    paginator = Paginator(archived_sheets, 60)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'administrator/archived_sheets.html', {
        'page_obj': page_obj,
        'query': query
    })



@user_passes_test(lambda user: is_in_group(user, "administrator"))
def unarchive_sheet(request, sheet_id):
    # Fetch the sheet by ID
    sheet = get_object_or_404(Sheet, id=sheet_id)
    
    # Update the is_done field to False (unarchive)
    sheet.is_archived = False
    sheet.save()

    # Redirect to the same page (to maintain pagination and filtering)
    referer_url = request.META.get('HTTP_REFERER', 'administrator:archived-sheets')
    return redirect(referer_url)