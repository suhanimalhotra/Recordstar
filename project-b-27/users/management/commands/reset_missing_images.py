from django.core.management.base import BaseCommand
from users.models import Profile, CD
import boto3
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset missing profile images to default'

    def handle(self, *args, **options):
        s3 = boto3.client('s3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

        reset_count = 0
        for profile in Profile.objects.all():
            if profile.image and profile.image.name != 'profile_pics/default.jpg':
                try:
                    s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=profile.image.name)
                except:
                    self.stdout.write(f"Resetting image for {profile.user.username}")
                    profile.image = 'profile_pics/default.jpg'
                    profile.save()
                    reset_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully reset {reset_count} profile images'))

        # Reset CD cover images
        cd_reset_count = 0
        for cd in CD.objects.all():
            if cd.cover_image and cd.cover_image.name:
                try:
                    s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=cd.cover_image.name)
                except:
                    self.stdout.write(f"Resetting cover image for CD: {cd.title}")
                    cd.cover_image = None  # Or set a default image path if you have one
                    cd.save()
                    cd_reset_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully reset {cd_reset_count} CD cover images'))