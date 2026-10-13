from decimal import Decimal
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from properties.embeddings import embed_text
from properties.models import Amenity, Location, Property

NUMBERS = ["latitude", "longitude", "price_per_night", "bedrooms", "bathrooms",
           "sleeps", "area_sqft", "city_latitude", "city_longitude"]
REQUIRED = ["external_id", "title", "city", "country", "latitude", "longitude", "price_per_night"]


class Command(BaseCommand):
    help = "Import vacation rental properties from a CSV (using pandas), then embed location names into pgvector."

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", default="bangladesh_properties_synthetic.csv",
                            help="CSV in the project root")
        parser.add_argument("--dry-run", action="store_true", help="Parse file but do not save changes")
        parser.add_argument("--update", action="store_true",
                            help="Update existing properties (matched by external_id)")

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / options["csvfile"]

        # 1. read + clean with pandas
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            raise CommandError(f"Failed to read CSV: {exc}")

        df.columns = df.columns.str.strip().str.lower()
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            raise CommandError(f"CSV is missing column(s): {', '.join(missing)}")
        for col in NUMBERS:
            df[col] = pd.to_numeric(df[col], errors="coerce") if col in df.columns else None

        total = len(df)
        df = df.dropna(subset=REQUIRED)                    
        df = df[df["price_per_night"] > 0]                 
        df = df.drop_duplicates("external_id")            
        df = df.reindex(columns=list(df.columns) + [c for c in ["state", "description", "address", "amenities", "property_type"] if c not in df.columns])
        df = df.fillna({"state": "", "description": "", "address": "", "amenities": ""})
        df = df.astype(object).where(df.notna(), None)   
        skipped = total - len(df)

        # 2. save to Postgres
        created = updated = 0
        with transaction.atomic():
            for row in df.itertuples(index=False):
                city_point = Point(float(row.city_longitude if row.city_longitude is not None else row.longitude),
                                   float(row.city_latitude if row.city_latitude is not None else row.latitude),
                                   srid=4326)
                location, _ = Location.objects.get_or_create(
                    city=row.city, state=row.state, country=row.country, defaults={"point": city_point},
                )

                data = dict(
                    location=location, title=row.title, description=row.description,
                    property_type=row.property_type or "house",
                    price=Decimal(str(row.price_per_night)),
                    bedrooms=int(row.bedrooms or 0),
                    bathrooms=Decimal(str(row.bathrooms or 0)),
                    sleeps=int(row.sleeps or 2),
                    area_sqft=int(row.area_sqft) if row.area_sqft is not None else None,
                    address=row.address,
                    point=Point(float(row.longitude), float(row.latitude), srid=4326),
                )

                external_id = str(row.external_id)
                prop = Property.objects.filter(external_id=external_id).first()
                if prop and not options["update"]:
                    skipped += 1
                    continue
                if prop:
                    for key, value in data.items():
                        setattr(prop, key, value)
                    updated += 1
                else:
                    prop = Property(external_id=external_id, **data)
                    created += 1
                prop.save()

                names = [a.strip() for a in row.amenities.split("|") if a.strip()]
                prop.amenities.set([Amenity.objects.get_or_create(name=n)[0] for n in names])

            if options["dry_run"]:
                transaction.set_rollback(True)

        suffix = " (dry run)" if options["dry_run"] else ""
        self.stdout.write(f"Imported: created={created}, updated={updated}, skipped={skipped}{suffix}")
        if options["dry_run"]:
            return

        # 3. embed location names that don't have a vector yet
        locations = list(Location.objects.filter(embedding__isnull=True))
        for loc in locations:
            loc.embedding = embed_text(loc.full_name)
            loc.save(update_fields=["embedding"])
        self.stdout.write(f"Embedded {len(locations)} location(s).")