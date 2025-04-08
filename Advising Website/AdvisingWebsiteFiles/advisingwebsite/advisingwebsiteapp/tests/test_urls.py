from django.test import SimpleTestCase
from django.urls import reverse, resolve
from advisingwebsiteapp import views
from django.contrib.auth.views import LogoutView

#Checking all urls to make sure that they are showing the correct views and are functioning as intended.

class TestUrls(SimpleTestCase):
    def test_home_url_resolves(self):
        url = reverse("home")
        self.assertEqual(resolve(url).func, views.home)

    def test_login_url_resolves(self):
        url = reverse("login")
        self.assertEqual(resolve(url).func, views.login_view)

    def test_register_url_resolves(self):
        url = reverse("register")
        self.assertEqual(resolve(url).func, views.register)

    def test_upload_transcript_url_resolves(self):
        url = reverse("uploadTranscript")
        self.assertEqual(resolve(url).func, views.upload_transcript)

    def test_logout_url_resolves(self):
        url = reverse("logout")
        self.assertEqual(resolve(url).func.view_class, LogoutView)

    def test_profile_url_resolves(self):
        url = reverse("profile")
        self.assertEqual(resolve(url).func, views.profile)

    def test_update_profile_url_resolves(self):
        url = reverse("update_profile")
        self.assertEqual(resolve(url).func, views.update_profile)

    def test_change_password_url_resolves(self):
        url = reverse("changePassword")
        self.assertEqual(resolve(url).func, views.change_password)

    def test_chat_url_resolves(self):
        url = reverse("chatHome")
        self.assertEqual(resolve(url).func, views.chathome)

    def test_chat_room_url_resolves(self):
        url = reverse("room", kwargs={'chat_id': 1})
        self.assertEqual(resolve(url).func, views.room)

    def test_chat_membership_url_resolves(self):
        url = reverse("check_chat_membership", kwargs={'chat_id': 1})
        self.assertEqual(resolve(url).func, views.check_chat_membership)

    def test_error_url_resolves(self):
        url = reverse("error_page")
        self.assertEqual(resolve(url).func, views.error_page)