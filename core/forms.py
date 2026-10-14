from django import forms

class LocationSearchForm(forms.Form):
    location_query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'hero-search-input',
            'placeholder': 'Try "Bandarban"',
            "autocomplete": "off",
        })
    )