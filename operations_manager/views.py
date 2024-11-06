from django.contrib import messages
from main.models import (Lead, SalesTeams, UserLeader, Sheet, Lead, LeadContactNames, LeadEmails, LeadPhoneNumbers,
                        UserLeader, SalesShow, Sheet, ReadyShow, PriceRequest, Referral, LeadsColors, Notification)
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AssignLeadsToLeaderForm
from django.contrib.auth.decorators import user_passes_test
from main.custom_decorators import is_in_group
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from main.custom_decorators import is_in_group
import logging
from django.db.models import OuterRef, Subquery, Q
from django.utils import timezone
from .forms import PriceRequestForm


logger = logging.getLogger('custom')

def index(request):
    query = request.GET.get('q')
    
    # Get the most recent phone number, email, and contact name
    recent_phone_number = LeadPhoneNumbers.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]
    recent_email = LeadEmails.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]
    recent_contact_name = LeadContactNames.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]

    if query:
        leads = Lead.objects.filter(name__icontains=query).order_by("-id")
    else:
        leads = Lead.objects.all().order_by("-id")
    
    # Annotate leads with recent contact information
    leads = leads.annotate(
        recent_phone_number=Subquery(recent_phone_number),
        recent_email=Subquery(recent_email),
        recent_contact_name=Subquery(recent_contact_name)
    )
    
    page = request.GET.get('page', '')
    paginator = Paginator(leads, 30)  

    try:
        leads_page = paginator.page(page)
    except PageNotAnInteger:
        leads_page = paginator.page(1)
    except EmptyPage:
        leads_page = paginator.page(paginator.num_pages)

    return render(request, 'operations_manager/index.html', {
        'leads': leads_page,
        'query': query
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def manage_leads_teams(request):
    operations_leaders = User.objects.filter(groups__name="operations_team_leader")

    paginator_operations = Paginator(operations_leaders, 5)  # Show 5 operations team leaders per page

    page_number_operations = request.GET.get('page_operations')
    
    page_operations = paginator_operations.get_page(page_number_operations)

    if request.method == 'POST' and 'remove_member' in request.POST:
        leader_id = request.POST.get('leader_id')
        user_id = request.POST.get('user_id')
        leader = get_object_or_404(User, id=leader_id)
        user = get_object_or_404(User, id=user_id)
        UserLeader.objects.filter(user=user, leader=leader).delete()
        return redirect('operations_manager:manage-leads-teams')  

    context = {
        "operations_team_leader": page_operations,
        "paginator_operations": paginator_operations,
    }

    return render(request, "operations_manager/manage_teams.html", context)


# Assign Each Lead Member to his Team Leader
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def assign_lead_to_leader(request):
    if request.method == 'POST':
        form = AssignLeadsToLeaderForm(request.POST)
        
        if form.is_valid():
            user = form.cleaned_data['user']
            leader = form.cleaned_data['leader']

            UserLeader.objects.get_or_create(user=user, leader=leader)

            return redirect('operations_manager:manage-leads-teams') 
    else:
        form = AssignLeadsToLeaderForm()
    
    operations_team_leaders = User.objects.filter(groups__name='operations_team_leader')
    
    context = {
        'form': form,
        'operations_team_leaders': operations_team_leaders,
    }
    
    return render(request, "operations_manager/assign_leads_to_leader.html", context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def sheet_detail(request, sheet_id):
    sheet = get_object_or_404(Sheet, id=sheet_id)
    leads = sheet.leads.all()

    return render(request, "operations_manager/sheet_detail.html", {
        "sheet": sheet,
        "leads": leads,
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def cut_ready_show_into_sales_shows(request, ready_show_id):
    # Get the ReadyShow and mark it as done
    ready_show = get_object_or_404(ReadyShow, id=ready_show_id)
    ready_show.is_done = True
    ready_show.done_date = timezone.now()
    ready_show.save()

    # Get the leads associated with the ReadyShow and group by time zone
    time_zones = ['cen', 'est', 'pac']
    leads_by_zone = {tz: list(ready_show.leads.filter(time_zone=tz)) for tz in time_zones}

    # Calculate the total number of leads and determine the number of SalesShows needed
    total_leads = sum(len(leads) for leads in leads_by_zone.values())

    # Determine how many SalesShows to create based on the number of leads
    if total_leads <= 20:
        sales_shows_count = 1
    elif 20 < total_leads <= 50:
        sales_shows_count = 2
    elif 50 < total_leads <= 100:
        sales_shows_count = 4
    elif 100 < total_leads <= 200:
        sales_shows_count = 8
    elif 200 < total_leads <= 400:
        sales_shows_count = 16
    elif 400 < total_leads <= 800:
        sales_shows_count = 32
    elif 800 < total_leads <= 1600:
        sales_shows_count = 64
    else:
        sales_shows_count = total_leads // 100  # Continuing the pattern (dividing by 100 for very large groups)

    # Create empty lists for each SalesShow to hold leads
    sales_show_leads = [[] for _ in range(sales_shows_count)]

    # Distribute leads from each time zone across the SalesShow objects evenly
    for tz, leads in leads_by_zone.items():
        zone_lead_count = len(leads)
        split_size = zone_lead_count // sales_shows_count

        # Split leads evenly among the SalesShow objects
        for i in range(sales_shows_count):
            start_index = i * split_size
            end_index = start_index + split_size
            sales_show_leads[i].extend(leads[start_index:end_index])

        # Handle leftover leads (if any) from the current time zone
        leftover_leads = leads[sales_shows_count * split_size:]
        for i, lead in enumerate(leftover_leads):
            sales_show_leads[i % sales_shows_count].append(lead)

    # Create SalesShows and assign the leads to them
    for idx, leads_chunk in enumerate(sales_show_leads, start=1):
        sales_show_name = f"{ready_show.sheet.name} ({idx})"  # Append number to SalesShow name
        sales_show = SalesShow.objects.create(
            name=sales_show_name,
            sheet=ready_show.sheet,
            is_done=False,
            label=ready_show.label
        )
        sales_show.leads.add(*leads_chunk)
        sales_show.save()

    return redirect(request.META.get('HTTP_REFERER', 'operations_manager:ready-shows'))


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def sales_shows_by_label(request, label=None):
    if label not in ['EHUB', 'EHUB2', 'EP']:
        label = 'EHUB'

    # Fetch SalesShows by the label of the associated ReadyShow
    sales_shows = SalesShow.objects.filter(label=label)

    # Get all users in the 'Sales' group
    sales_group = Group.objects.get(name='Sales')
    sales_agents = sales_group.user_set.all()

    context = {
        'sales_shows': sales_shows,
        'active_label': label,
        'sales_agents': sales_agents,
    }
    return render(request, 'operations_manager/sales_shows.html', context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def assign_sales_show(request):
    if request.method == 'POST':
        show_id = request.POST.get('assign_show_id')
        show = get_object_or_404(SalesShow, id=show_id)

        # Get the selected agent ID from the form
        agent_id = request.POST.get(f'agent_id_{show_id}')
        if agent_id:
            agent = get_object_or_404(User, id=agent_id)

            # Assign the selected agent to the show
            show.Agent = agent
            show.save()

    return redirect(request.META.get('HTTP_REFERER', 'operations_manager:sales-shows'))


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def ready_shows_view(request, label=None):
    # If no label is passed, default to 'EHUB'
    if label not in ['EHUB', 'EHUB2', 'EP']:
        label = 'EHUB'

    # Filter ReadyShows based on the label
    ready_shows = ReadyShow.objects.filter(label=label, is_done=False).order_by("-id")

    # Pagination
    paginator = Paginator(ready_shows, 30)  # Show 10 items per page (you can adjust thiss)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass the active label and paginated queryset to the template
    context = {
        'ready_shows': page_obj,  # Use paginated queryset
        'active_label': label,
    }

    return render(request, 'operations_manager/ready_shows.html', context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def done_ready_shows(request, label=None):
    # Default label if not passed
    if label not in ['EHUB', 'EHUB2', 'EP']:
        label = 'EHUB'
    
    # Filter Done ReadyShows based on the label
    done_shows = ReadyShow.objects.filter(label=label, is_done=True).order_by("-id")

    # Pagination
    paginator = Paginator(done_shows, 30)  # Show 10 items per page (adjust this number as needed)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass the active label and paginated queryset to the template
    context = {
        'done_shows': page_obj,  # Use paginated queryset
        'active_label': label,
    }

    return render(request, 'operations_manager/done_ready_shows.html', context)


# View for Unassigned Sales Shows
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def unassigned_sales_shows(request, label='EHUB'):
    # Get unassigned shows based on the label
    unassigned_shows = SalesShow.objects.filter(Agent__isnull=True, label=label).order_by("-id")
    
    # Pagination
    paginator = Paginator(unassigned_shows, 40)  # Show 10 items per page (you can adjust this)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    timezone_counts = {}
    for show in page_obj:
        # Count leads based on the time zone
        est_count = show.leads.filter(time_zone='EST').count()
        cen_count = show.leads.filter(time_zone='CEN').count()
        pac_count = show.leads.filter(time_zone='PAC').count()

        # Store counts in dictionary with show ID as the key
        timezone_counts[show.id] = {
            'est': est_count,
            'cen': cen_count,
            'pac': pac_count,
        }

    # Get sales managers, team leaders, and sales team
    sales_managers = User.objects.filter(groups__name='sales_manager')
    team_leader = SalesTeams.objects.values('leader')
    sales_team = User.objects.filter(Q(groups__name='sales') & Q(id__in=UserLeader.objects.filter(leader_id__in=team_leader).values('user'))).distinct()
    openers_closers = User.objects.filter(id__in=SalesTeams.objects.values('openers_closers')).distinct()
    leader_user = User.objects.filter(id__in=team_leader)
    sales_agents = sales_managers.union(sales_team, leader_user, openers_closers)

    # Create a dictionary to hold counts of leads with colors
    blue_red_leads_counts = {}
    for show in page_obj:
        blue_red_leads_counts[show.id] = LeadsColors.objects.filter(lead__in=show.leads.all(), sheet=show.sheet, color__in=['blue', 'red']).count()

    context = {
        'unassigned_shows': page_obj,  # Use paginated queryset
        'label': label,
        'sales_agents': sales_agents,
        'active_label': label,
        'blue_red_leads_counts': blue_red_leads_counts,
        'timezone_counts': timezone_counts,
    }

    return render(request, 'operations_manager/unassigned_sales_shows.html', context)


# View for Assigned Sales Shows
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def assigned_sales_shows(request, label='EHUB'):
    assigned_shows = SalesShow.objects.filter(Agent__isnull=False, label=label).order_by("-id")
    context = {
        'assigned_shows': assigned_shows,
        'label': label,
        'active_label': label,
    }
    return render(request, 'operations_manager/assigned_sales_shows.html', context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def view_sales_agents(request):
    sales_group = Group.objects.get(name='sales')
    sales_team_leader_group = Group.objects.get(name='sales_team_leader')
    sales_manager_group = Group.objects.get(name='sales_manager')

    # Get all users who belong to one of these groups
    agents = User.objects.filter(groups__in=[sales_group, sales_team_leader_group, sales_manager_group]).distinct()

    context = {
        'agents':agents
    }

    return render(request, "operations_manager/view_agents.html", context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def view_agent_done_shows(request, agent_id):
    agent = get_object_or_404(User, id=agent_id)

    if request.method == 'POST':
        show_id = request.POST.get('show_id')
        show = get_object_or_404(SalesShow, id=show_id, Agent=agent)

        # Recycle the show
        show.is_recycled = True
        show.rec_date = timezone.now()
        show.save()

        messages.success(request, f'Show "{show.name}" has been recycled.')

    # Fetch all done shows for the agent
    shows = SalesShow.objects.filter(is_done=True, Agent=agent, is_recycled=False, is_done_rec=False)
    
    context = {
        'agent': agent,
        'shows': shows
    }

    return render(request, "operations_manager/view_agent_done_shows.html", context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def price_requests_view(request):
    if request.method == 'POST':
        form = PriceRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('operations_manager:price_request')
    else:
        form = PriceRequestForm()

    price_requests_list = PriceRequest.objects.all().order_by("-id")
    
    # Set up pagination
    paginator = Paginator(price_requests_list, 20)  # Show 10 requests per page
    page_number = request.GET.get('page')
    price_requests = paginator.get_page(page_number)

    context = {
        'price_requests': price_requests,
        'form': form,
    }
    
    return render(request, 'operations_manager/price_request.html', context)



@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def update_price_requests(request):
    if request.method == 'POST':
        for key in request.POST:
            if key.startswith('email_status_'):
                request_id = key.split('_')[2]
                email_status = request.POST[key]
                PriceRequest.objects.filter(id=request_id).update(email_status=email_status)
            elif key.startswith('lead_status_'):
                request_id = key.split('_')[2]
                lead_status = request.POST[key]
                PriceRequest.objects.filter(id=request_id).update(lead_status=lead_status)
        return redirect('operations_manager:price-requests')  # Redirect to the price requests list page
    else:
        return redirect('operations_manager:price-requests')  # Handle non-POST requests


@user_passes_test(lambda user: is_in_group(user, "operations_manager") or is_in_group(user, "sales_manager"))
def manage_referrals(request):
    referrals_list = Referral.objects.all().order_by("-entry_date")

    # Create a dictionary to store unique referrals based on lead and sheet
    unique_referrals = {}
    for referral in referrals_list:
        key = (referral.lead.id, referral.sheet.id)  # Use lead and sheet as a unique key
        if key not in unique_referrals:
            unique_referrals[key] = referral

    # Now unique_referrals contains only the latest referral per lead and sheet combination
    referrals_list_2 = list(unique_referrals.values())

    paginator = Paginator(referrals_list_2, 30)  # 30 referrals per page

    page_number = request.GET.get('page')
    referrals = paginator.get_page(page_number)

    return render(request, 'operations_manager/manage_referrals.html', {
        'referrals': referrals,
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def notifications(request):
    user = request.user
    notifications_for_user = Notification.objects.filter(
        receiver=user).order_by('-created_at')

    # Implement pagination
    page = request.GET.get('page', '')
    # Show 10 notifications per page
    paginator = Paginator(notifications_for_user, 20)

    try:
        notifications_page = paginator.page(page)
    except PageNotAnInteger:
        notifications_page = paginator.page(1)
    except EmptyPage:
        notifications_page = paginator.page(paginator.num_pages)

    return render(request, 'operations_manager/notifications.html', {
        'notifications': notifications_page
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def delete_sales_show(request, show_id):
    if request.method == 'POST':
        show = get_object_or_404(SalesShow, id=show_id)  # Fetch the show by ID
        show.delete()  # Delete the show
        
        # Get the active tab from the request
        active_label = request.POST.get('active_label', 'EHUB')  # Default to 'EHUB' if not provided
        return redirect('operations_manager:unassigned-sales-shows', active_label)  # Redirect to the active tab
