import uuid

from django.contrib.gis.db import models
from django.urls import reverse
from django.utils.text import slugify
from pgvector.django import HnswIndex, VectorField

TEXT_EMBEDDING_DIMS = 384
IMAGE_EMBEDDING_DIMS = 768     


class Location(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    point = models.PointField(geography=True, srid=4326, null=True, blank=True)
    boundary = models.MultiPolygonField(srid=4326, null=True, blank=True)
    embedding = VectorField(dimensions=TEXT_EMBEDDING_DIMS, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["country", "state", "city"]
        constraints = [
            models.UniqueConstraint(fields=["city", "state", "country"], name="uniq_location_city_state_country"),
        ]
        indexes = [
            HnswIndex(
                name="location_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"], 
            ),
        ]

    @property
    def full_name(self):
        return ", ".join(p for p in (self.city, self.state, self.country) if p)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.city
        if not self.slug:
            self.slug = slugify(self.full_name)[:255]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "amenities"

    def __str__(self):
        return self.name


class Property(models.Model):
    class PropertyType(models.TextChoices):
        HOUSE = "house", "House"
        VILLA = "villa", "Villa"
        CONDO = "condo", "Condo"
        APARTMENT = "apartment", "Apartment"
        CABIN = "cabin", "Cabin"
        COTTAGE = "cottage", "Cottage"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        BOOKED = "booked", "Booked"
        INACTIVE = "inactive", "Inactive"

    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)  
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="properties")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    property_type = models.CharField(max_length=50, choices=PropertyType.choices, default=PropertyType.HOUSE)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.AVAILABLE)
    price = models.DecimalField(max_digits=14, decimal_places=2)            
    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=0)  
    sleeps = models.PositiveSmallIntegerField(default=2)
    area_sqft = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    address = models.TextField(blank=True)
    point = models.PointField(geography=True, srid=4326, null=True, blank=True)
    footprint = models.PolygonField(srid=4326, null=True, blank=True)
    embedding = VectorField(dimensions=TEXT_EMBEDDING_DIMS, null=True, blank=True)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="properties")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]
        verbose_name_plural = "properties"
        indexes = [
            models.Index(fields=["price"]),
            models.Index(fields=["bedrooms"]),
            HnswIndex(
                name="property_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.title)[:200]}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("properties:detail", kwargs={"slug": self.slug})

    @property
    def primary_image(self):
        images = list(self.images.all())         
        for img in images:
            if img.is_primary:
                return img
        return images[0] if images else None

    @property
    def image_path(self):
        images = {
            "apartment": "img/appartment.jpg",
            "house": "img/house.jpg",
            "condo": "img/condo.jpg",
            "cabin": "img/cabin.jpg",
            "cottage": "img/cottage.jpg",
            "villa" :"img/villa.jpg"
        }

        return images.get(self.property_type, "img/default.jpg")

    def __str__(self):
        return self.title


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="properties/%Y/%m/", width_field="width", height_field="height")
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.TextField(blank=True)
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)    
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    file_size = models.BigIntegerField(null=True, blank=True, editable=False)
    embedding = VectorField(dimensions=IMAGE_EMBEDDING_DIMS, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "sort_order", "id"]

    def save(self, *args, **kwargs):
        if self.image and not self.file_size:
            try:
                self.file_size = self.image.size
            except (OSError, ValueError):
                pass
        super().save(*args, **kwargs)
        if self.is_primary:    
            PropertyImage.objects.filter(property=self.property).exclude(pk=self.pk).update(is_primary=False)

    def __str__(self):
        return f"Image {self.pk} of property {self.property_id}"