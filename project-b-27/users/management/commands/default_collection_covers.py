from django.core.management.base import BaseCommand
from users.models import Collection
import boto3
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset missing collection cover images to default'

    def handle(self, *args, **options):
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        reset_count = 0
        for coll in Collection.objects.all():
            # Only consider ones not already using the default
            if coll.cover_image and coll.cover_image.name != 'collection_covers/default.jpg':
                try:
                    # Check if the object exists in S3
                    s3.head_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=coll.cover_image.name
                    )
                except Exception:
                    self.stdout.write(f"Resetting cover image for collection: {coll.name}")
                    coll.cover_image = 'collection_covers/default.jpg'
                    coll.save(update_fields=['cover_image'])
                    reset_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully reset {reset_count} collection cover images"
        ))
