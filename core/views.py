from django.shortcuts import render
from .forms import LocationSearchForm

"""
Views for the core app.
"""


def home(request):
    """
    Render the home template.
    """
    return render(request, 'home.html', {'search_form': LocationSearchForm()})