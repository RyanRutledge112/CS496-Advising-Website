from django.test import SimpleTestCase
from django.urls import reverse, resolve
from advisingwebsiteapp import views
from django.contrib.auth.views import LogoutView

#Checking all urls to make sure that they are showing the correct views and are functioning as intended.

class TestUrls(SimpleTestCase):
    def test_home_url_resolves(self):
        url = reverse("home")
        self.assertEqual(resolve(url).func.view_class, views.home)

    def test_login_url_resolves(self):
        url = reverse("login")
        self.assertEqual(resolve(url).func.view_class, views.login_view)

    def test_register_url_resolves(self):
        url = reverse("register")
        self.assertEqual(resolve(url).func.view_class, views.register)

    def test_upload_transcript_url_resolves(self):
        url = reverse("uploadTranscript")
        self.assertEqual(resolve(url).func.view_class, views.upload_transcript)

    def test_logout_url_resolves(self):
        url = reverse("logout")
        self.assertEqual(resolve(url).func.view_class, LogoutView.as_view())

    def test_profile_url_resolves(self):
        url = reverse("profile")
        self.assertEqual(resolve(url).func.view_class, views.profile)

    def test_update_profile_url_resolves(self):
        url = reverse("update_profile")
        self.assertEqual(resolve(url).func.view_class, views.update_profile)

    def test_change_password_url_resolves(self):
        url = reverse("changePassword")
        self.assertEqual(resolve(url).func.view_class, views.change_password)

    def test_chat_url_resolves(self):
        url = reverse("chat")
        self.assertEqual(resolve(url).func.view_class, views.chathome)

    def test_chat_room_url_resolves(self):
        url = reverse("chat/1/")
        self.assertEqual(resolve(url).func.view_class, views.room)

    def test_chat_membership_url_resolves(self):
        url = reverse("chat/chat-membership/1/")
        self.assertEqual(resolve(url).func.view_class, views.check_chat_membership)

    def test_error_url_resolves(self):
        url = reverse("error")
        self.assertEqual(resolve(url).func.view_class, views.error_page)