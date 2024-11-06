from django import forms
from django.forms import inlineformset_factory
from main.models import Sheet, Lead, LeadPhoneNumbers, LeadEmails, LeadContactNames
from django.contrib.auth.models import User
from main.models import UserLeader

LeadPhoneNumbersFormSet = inlineformset_factory(
    Lead, LeadPhoneNumbers, fields=('value',), extra=1, can_delete=True
)

LeadEmailsFormSet = inlineformset_factory(
    Lead, LeadEmails, fields=('value',), extra=1, can_delete=True
)

LeadContactNamesFormSet = inlineformset_factory(
    Lead, LeadContactNames, fields=('value',), extra=1, can_delete=True
)


class AssignLeadsToLeaderForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='leads').exclude(id__in=UserLeader.objects.values('user')),
        label='Select User'
    )
    leader = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='operations_team_leader'),
        label='Select Team Leader'
    )

class LeadForm(forms.ModelForm):
    sheets = forms.ModelMultipleChoiceField(
        queryset=Sheet.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        help_text='Select one or more sheets from the dropdown.',
    )
    phone_numbers = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter phone numbers separated by commas'}),
        required=False,
        help_text='Enter multiple phone numbers separated by commas.'
    )
    emails = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter emails separated by commas'}),
        required=False,
        help_text='Enter multiple emails separated by commas.'
    )
    contact_names = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter contact names separated by commas'}),
        required=False,
        help_text='Enter multiple contact names separated by commas.'
    )

    class Meta:
        model = Lead
        fields = ['name', 'time_zone', 'sheets', 'phone_numbers', 'emails', 'contact_names']
