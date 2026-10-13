from django.http import JsonResponse
from .models import Location, Property
from .embeddings import embed_text
from pgvector.django import CosineDistance
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "message": "property api is healthy!",
    })


def autocomplete_locations(request):
    search = request.GET.get("search","").strip()
    if len(search) < 2:
        return JsonResponse({"results": []})
    
    embeded_search = embed_text(search)

    suggested_locations = (
        Location.objects
        .filter(is_active=True, embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", embeded_search))
        .order_by("distance")[:5]
    )

    results = []
    for loc in suggested_locations:
        results.append({"id": loc.id, "name": loc.full_name, "distance": round(loc.distance, 4)})
    return JsonResponse({"results": results})


FIELDS = [
    "id", "external_id", "location_id", "title", "slug", "description",
    "property_type", "status", "price", "bedrooms", "bathrooms", "sleeps",
    "area_sqft", "address", "is_featured", "is_active", "created_at", "updated_at",
]
def get_properties_by_location(request):
    location_id = request.GET.get("location_id", "").strip()

    try:
        limit = int(request.GET.get("limit", 10))
        offset = int(request.GET.get("offset", 0))
    except ValueError:
        return JsonResponse({"error": "limit and offset must be integers"}, status=400)

    if not location_id:
        return JsonResponse(
            {"error": "location_id is required"},
            status=400,
        )

    if limit < 1 or limit > 100 or offset < 0:
        return JsonResponse(
            {"error": "Invalid limit or offset"},
            status=400,
        )


    queryset = Property.objects.filter(location_id=location_id).order_by("id")
    properties = list(queryset.values(*FIELDS)[offset:offset + limit])

    return JsonResponse({"total": queryset.count(), "limit":limit, "offset": offset, "result": properties})


def get_nearby_properties(request) :
    try:
        property_id = int(request.GET.get("id", ""))
        radius_km = float(request.GET.get("radius_km", 5))
        limit = int(request.GET.get("limit", 10))
    except ValueError:
        return JsonResponse({"error": "id, radius_km and limit must be numbers"}, status=400)

    if not (0 < radius_km <= 100) or not (1 <= limit <= 100):
        return JsonResponse({"error": "radius_km must be 0-100 and limit 1-100"}, status=400)

    prop = Property.objects.filter(id=property_id).first()

    if prop is None:
        return JsonResponse({"error": "Property not found"}, status=404)
    if prop.point is None:
        return JsonResponse({"error": "Property has no coordinates"}, status=400)

    nearby = (
        Property.objects
        .filter(is_active=True, point__dwithin=(prop.point, D(km=radius_km)))   
        .exclude(id=prop.id)                                                     
        .annotate(distance=Distance("point", prop.point))                        
        .order_by("distance")[:limit]                                            
    )

    properties = list(nearby.values(*FIELDS))
    return JsonResponse({"property_id": prop.id, "radius_km": radius_km, "results": properties})