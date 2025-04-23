from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
import time

class PageLoadTimeTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Firefox()
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def test_home_page_loads_under_3_seconds(self):
        start = time.time()
        self.driver.get(f'{self.live_server_url}/home')
        end = time.time()
        load_time = end - start
        print(f"Home page load time: {load_time:.2f} seconds")
        self.assertLess(load_time, 3, "Home page load took too long")

    def test_register_page_loads_under_3_seconds(self):
        start = time.time()
        self.driver.get(f'{self.live_server_url}/register')
        end = time.time()
        load_time = end - start
        print(f"Register page load time: {load_time:.2f} seconds")
        self.assertLess(load_time, 3, "Register page load took too long")

    def test_upload_page_loads_under_3_seconds(self):
        start = time.time()
        self.driver.get(f'{self.live_server_url}/uploadTranscript')
        end = time.time()
        load_time = end - start
        print(f"Upload Transcript page load time: {load_time:.2f} seconds")
        self.assertLess(load_time, 3, "Upload Transcript page load took too long")

    def test_profile_page_loads_under_3_seconds(self):
        start = time.time()
        self.driver.get(f'{self.live_server_url}/profile')
        end = time.time()
        load_time = end - start
        print(f"Profile page load time: {load_time:.2f} seconds")
        self.assertLess(load_time, 3, "Profile page load took too long")

    def test_login_page_loads_under_3_seconds(self):
        start = time.time()
        self.driver.get(f'{self.live_server_url}/login')
        end = time.time()
        load_time = end - start
        print(f"Login page load time: {load_time:.2f} seconds")
        self.assertLess(load_time, 3, "Login page load took too long")

    def test_change_password_page_loads_under_3_seconds(self):
        start = time.time()
        self.driver.get(f'{self.live_server_url}/changePassword')
        end = time.time()
        load_time = end - start
        print(f"Change Password page load time: {load_time:.2f} seconds")
        self.assertLess(load_time, 3, "Change Password page load took too long")

    def test_recommended_classes_page_loads_under_3_seconds(self):
        start = time.time()
        self.driver.get(f'{self.live_server_url}/recommendedClasses')
        end = time.time()
        load_time = end - start
        print(f"Recommended classes page load time: {load_time:.2f} seconds")
        self.assertLess(load_time, 3, "Recommended classes page load took too long")