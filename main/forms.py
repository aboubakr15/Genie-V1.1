from django import forms
from .models import Sheet, FilterWords, FilterType

class ImportSheetsForm(forms.Form):
    folder_path = forms.CharField(label='Folder Path', max_length=255)

# Without acceptance for operations managers and team leader
class AutoFillForm(forms.Form):
    file = forms.FileField(required=True, label="Choose a file")
    latest_sheet = forms.ModelChoiceField(
        queryset=Sheet.objects.all(), 
        required=False, 
        label="Select a Sheet",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class FilterWordsForm(forms.ModelForm):
    filter_types = forms.ModelMultipleChoiceField(
        queryset=FilterType.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # This will show the filter types as checkboxes
        required=True
    )

    class Meta:
        model = FilterWords
        fields = ['word', 'filter_types']