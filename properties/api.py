from django.http import JsonResponse
from .models import Location
from .embeddings import embed_text
from pgvector.django import CosineDistance


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

