from django.test import TestCase, Client
from django.contrib.auth.models import User
from users.models import CD
from users.models import Profile
from django.urls import reverse

class CDModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.cd = CD.objects.create(
            title="Test Album",
            artist="Test Artist",
            release_year=2000,
            genre="Rock",
            description="A test album",
            owner=self.user
        )

    def test_cd_creation(self):
        """Test if a CD can be created correctly."""
        self.assertEqual(self.cd.title, "Test Album")
        self.assertEqual(self.cd.artist, "Test Artist")
        self.assertEqual(self.cd.release_year, 2000)
        self.assertEqual(self.cd.genre, "Rock")
        self.assertEqual(self.cd.description, "A test album")
        self.assertEqual(self.cd.owner, self.user)

    def test_cd_deletion(self):
        """Test if a CD can be deleted."""
        cd_id = self.cd.id
        self.cd.delete()
        self.assertFalse(CD.objects.filter(id=cd_id).exists())

class CDViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = self.user.profile
        self.profile.account_type = 'L'
        self.profile.save()
        self.client.login(username='testuser', password='testpass')
        self.cd = CD.objects.create(
            title="Test Album",
            artist="Test Artist",
            release_year=2000,
            genre="Rock",
            description="A test album",
            owner=self.user
        )

    def test_collection_page_loads(self):
        """Test if the collection page loads correctly."""
        response = self.client.get(reverse("collection"))
        self.assertEqual(response.status_code, 200)

    def test_add_cd_view(self):
        """Test if adding a CD works."""
        response = self.client.post("/recordstar/add_item/", {
            'title': 'New Album',
            'artist': 'New Artist',
            'release_year': 2021,
            'genre': 'Pop',
            'description': 'Another test album',
        })
        self.assertEqual(response.status_code, 302)  # Redirects after successful form submission
        self.assertTrue(CD.objects.filter(title="New Album").exists())

    def test_delete_cd_view(self):
        """Test if deleting a CD works."""
        response = self.client.post(f"/recordstar/delete_cd/{self.cd.id}/")
        self.assertEqual(response.status_code, 302)  # Redirects after deletion
        self.assertFalse(CD.objects.filter(id=self.cd.id).exists())


