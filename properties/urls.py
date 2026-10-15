from django.urls import path
from .api import health_check, autocomplete_locations
from .views import  get_properties_by_location, get_nearby_properties

urlpatterns = [
    # api paths 
    path("health/", health_check, name="health-check"),
    path("autocomplete/", autocomplete_locations, name="sematic-location"),

    # browser paths
    path("properties/", get_properties_by_location, name="get-properties-by-locations"),
    path("nearby-properties/", get_nearby_properties, name="get-nearby-properties",),
]