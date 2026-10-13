from django.contrib import admin
from django.utils.html import format_html

from .models import Amenity, Location, Property, PropertyImage


# ---------- custom list filters ----------
class PriceRangeFilter(admin.SimpleListFilter):
    title = "price per night"
    parameter_name = "price_range"

    def lookups(self, request, model_admin):
        return [("low", "Under 100"), ("mid", "100 - 250"), ("high", "Over 250")]

    def queryset(self, request, queryset):
        if self.value() == "low":
            return queryset.filter(price__lt=100)
        if self.value() == "mid":
            return queryset.filter(price__gte=100, price__lte=250)
        if self.value() == "high":
            return queryset.filter(price__gt=250)
        return queryset


class HasImagesFilter(admin.SimpleListFilter):
    title = "images"
    parameter_name = "has_images"

    def lookups(self, request, model_admin):
        return [("yes", "With images"), ("no", "Without images")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(images__isnull=False).distinct()
        if self.value() == "no":
            return queryset.filter(images__isnull=True)
        return queryset


# ---------- inline image upload + preview ----------
class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 2
    fields = ("image", "preview", "alt_text", "is_primary", "sort_order")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;border-radius:4px">', obj.image.url)
        return "-"


# ---------- model admins ----------
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin): 
    list_display = ("city", "state", "country", "is_active", "created_at")
    list_filter = ("country", "state", "is_active")
    search_fields = ("name", "city", "state", "country")
    readonly_fields = ("slug", "created_at", "updated_at")
    exclude = ("embedding",)
    ordering = ("country", "state", "city")


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "property_type", "price", "bedrooms", "is_featured", "created_at")
    list_filter = (PriceRangeFilter, HasImagesFilter, "property_type", "status", "location", "is_featured")
    search_fields = ("title", "description", "address", "external_id")
    readonly_fields = ("slug", "created_at", "updated_at")
    exclude = ("embedding",)
    autocomplete_fields = ("location",)
    filter_horizontal = ("amenities",)
    inlines = [PropertyImageInline]
    ordering = ("-created_at",)


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    search_fields = ("name",)