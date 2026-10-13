from django.urls import path
from .api import health_check, autocomplete_locations, get_properties_by_location

urlpatterns = [
    # api paths 
    path("health/", health_check, name="health-check"),

    # browser paths
    path("autocomplete/", autocomplete_locations, name="sematic-location"),
    path("properties/", get_properties_by_location , name="get-properties-by-locations")
]