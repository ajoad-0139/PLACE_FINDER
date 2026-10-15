from django.shortcuts import render
from .models import Property
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from rest_framework import serializers


class PropertyListQuerySerializer(serializers.Serializer):
    location_id = serializers.IntegerField(min_value=1)
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=9,
        required=False,
    )
    offset = serializers.IntegerField(
        min_value=0,
        default=0,
        required=False,
    )


class NearbyPropertiesQuerySerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    radius_km = serializers.FloatField(
        min_value=0.01,
        max_value=100,
        default=5,
        required=False,
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=12,
        required=False,
    )



# def get_properties_by_location(request):

#     try:
#         location_id = int(request.GET.get("location_id", "").strip())
#         limit = int(request.GET.get("limit", 9))
#         offset = int(request.GET.get("offset", 0))
#     except ValueError:
#         return render(
#             request,
#             "error.html",
#             {"error_message": "location_id, limit and offset must be integers"},
#             status=400,
#         )

#     if not location_id:
#         return render(
#             request,
#             "error.html",
#             {"error_message": "location_id is required"},
#             status=400,
#         )
#     if limit < 1 or limit > 100 or offset < 0:
#         return render(
#             request,
#             "error.html",
#             {"error_message": "Invalid limit or offset"},
#             status=400,
#         )
        


#     queryset = Property.objects.filter(location_id=location_id).order_by("id")

#     properties = (
#         queryset
#         .defer("embedding", "point", "footprint")
#         .prefetch_related("images")[offset:offset + limit]
#     )

#     total = queryset.count()

#     return render(request, "properties.html", {
#         "properties": properties,
#         "total": total,
#         "limit": limit,
#         "offset": offset,
#         "location_id": location_id,
#         "page": offset // limit + 1,
#         "total_pages": (total + limit - 1) // limit,
#         "has_prev": offset > 0,
#         "has_next": offset + limit < total,
#         "prev_offset": max(offset - limit, 0),
#         "next_offset": offset + limit,
#     })


# def get_nearby_properties(request) :

#     try:
#         property_id = int(request.GET.get("id", ""))
#         radius_km = float(request.GET.get("radius_km", 5))
#         limit = int(request.GET.get("limit", 12))
#     except ValueError:
#         return render(
#             request,
#             "error.html",
#             {"error_message": "property_id, limit and radius_km must be integers"},
#             status=400,
#         )

#     if not (0 < radius_km <= 100) or not (1 <= limit <= 100):
#         return render(
#             request,
#             "error.html",
#             {"error_message": "radius_km must be 0-100 and limit 1-100"},
#             status=400,
#         )

#     prop = (
#         Property.objects
#         .select_related("location")
#         .prefetch_related("images", "amenities")
#         .defer("embedding", "footprint")
#         .filter(id=property_id)
#         .first()
#     )

#     if prop is None:
#         return render(
#             request,
#             "error.html",
#             {"error_message": "Property not found"},
#             status=404,
#         )
#     if prop.point is None:
#         return render(
#             request,
#             "error.html",
#             {"error_message": "Property has no coordinates"},
#             status=400,
#         )

#     nearby = (
#         Property.objects
#         .filter(is_active=True, point__dwithin=(prop.point, D(km=radius_km)))
#         .exclude(id=prop.id)
#         .annotate(distance=Distance("point", prop.point))
#         .order_by("distance")
#         .defer("embedding", "footprint")
#         .prefetch_related("images")[:limit]
#     )

#     return render(request, "property-details.html", {
#         "property": prop,
#         "nearby_properties": nearby,
#     })



def get_properties_by_location(request):
    serializer = PropertyListQuerySerializer(data=request.GET)

    if not serializer.is_valid():
        return render(
            request,
            "error.html",
            {
                "error_message": (
                    "Invalid property search parameters. "
                    "Please check location_id, limit and offset."
                )
            },
            status=400,
        )

    location_id = serializer.validated_data["location_id"]
    limit = serializer.validated_data["limit"]
    offset = serializer.validated_data["offset"]

    queryset = Property.objects.filter(location_id=location_id).order_by("id")

    properties = (
        queryset
        .defer("embedding", "point", "footprint")
        .prefetch_related("images")[offset:offset + limit]
    )

    total = queryset.count()

    return render(
        request,
        "properties.html",
        {
            "properties": properties,
            "total": total,
            "limit": limit,
            "offset": offset,
            "location_id": location_id,
            "page": offset // limit + 1,
            "total_pages": (total + limit - 1) // limit,
            "has_prev": offset > 0,
            "has_next": offset + limit < total,
            "prev_offset": max(offset - limit, 0),
            "next_offset": offset + limit,
        },
    )


def get_nearby_properties(request):
    serializer = NearbyPropertiesQuerySerializer(data=request.GET)

    if not serializer.is_valid():
        return render(
            request,
            "error.html",
            {
                "error_message": (
                    "Invalid nearby-property search parameters. "
                    "Please check id, radius_km and limit."
                )
            },
            status=400,
        )

    property_id = serializer.validated_data["id"]
    radius_km = serializer.validated_data["radius_km"]
    limit = serializer.validated_data["limit"]

    prop = (
        Property.objects
        .select_related("location")
        .prefetch_related("images", "amenities")
        .defer("embedding", "footprint")
        .filter(id=property_id)
        .first()
    )

    if prop is None:
        return render(
            request,
            "error.html",
            {"error_message": "Property not found."},
            status=404,
        )

    if prop.point is None:
        return render(
            request,
            "error.html",
            {"error_message": "Property has no coordinates."},
            status=400,
        )

    nearby = (
        Property.objects
        .filter(
            is_active=True,
            point__dwithin=(prop.point, D(km=radius_km)),
        )
        .exclude(id=prop.id)
        .annotate(distance=Distance("point", prop.point))
        .order_by("distance")
        .defer("embedding", "footprint")
        .prefetch_related("images")[:limit]
    )

    return render(
        request,
        "property-details.html",
        {
            "property": prop,
            "nearby_properties": nearby,
        },
    )
