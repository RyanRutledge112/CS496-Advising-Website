from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from advisingwebsiteapp.models import Degree, UserDegree
from django.contrib import messages as django_messages
from django.contrib.messages import get_messages

User = get_user_model()

class AccountCreationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="Software Engineering",
            hours_needed=120,
            degree_type=1
        )
        self.register_url = reverse('register')

    def test_valid_user_registration(self):
        data = {
            'email': 'newuser@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'password': 'StrongPass123!',
            'student_id': 123456789,
            'is_student': True,
            'degrees[]': [str(self.degree.id)],
        }

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)  # Redirects after successful registration
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.student_id, 123456789)

        self.assertTrue(UserDegree.objects.filter(user_student_id=user, degree=self.degree).exists())

        # Check user is logged in
        self.assertIn('_auth_user_id', self.client.session)

    def test_invalid_email_format(self):
        data = {
            'email': 'not-an-email',
            'first_name': 'Invalid',
            'last_name': 'Email',
            'password': 'StrongPass123!',
            'student_id': 123123123,
            'is_student': True,
            'degrees[]': [str(self.degree.id)],
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.register_url)
        
        django_messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Invalid email format" in str(m) for m in django_messages))
        self.assertFalse(User.objects.filter(email='not-an-email').exists())

    def test_password_validation_failure(self):
        data = {
            'email': 'badpass@example.com',
            'first_name': 'Bad',
            'last_name': 'Password',
            'password': 'short',
            'student_id': 876543210,
            'is_student': True,
            'degree': self.degree.id
        }

        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.register_url)

        django_messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Password must be at least 9 characters long, include an uppercase letter, a number, and a special character." in str(m) for m in django_messages))

    def test_missing_required_fields(self):
        required_fields = ['email', 'first_name', 'last_name', 'password', 'student_id']
        base_data = {
            'email': 'requiredcheck@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'StrongPass123!',
            'student_id': 112233445,
            'is_student': True,
            'degrees[]': [str(self.degree.id)], 
        }

        # Test each required field missing individually
        for field in required_fields:
            data = base_data.copy()
            data.pop(field)  # Remove one required field
            response = self.client.post(self.register_url, data)
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.register_url)

            messages = list(response.wsgi_request._messages)
            self.assertTrue(any("required" in str(m).lower() for m in messages), msg=f"Missing field: {field} did not raise error.")

        # Test multiple fields missing
        data = base_data.copy()
        data.pop('email')
        data.pop('first_name')
        data.pop('password')

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.register_url)

        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("required" in str(m).lower() for m in messages), msg="Multiple missing fields did not raise error.")


    def test_multiple_degrees_selected(self):
        degree2 = Degree.objects.create(
            degree_name="Data Science",
            degree_number="DS202",
            concentration="Machine Learning",
            hours_needed=120,
            degree_type=1
        )

        data = {
            'email': 'multidegree@example.com',
            'first_name': 'Multi',
            'last_name': 'Degree',
            'password': 'StrongPass123!',
            'student_id': 987654321,
            'is_student': True,
            'degrees[]': [str(self.degree.id), str(degree2.id)],
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='multidegree@example.com').exists())
        user = User.objects.get(email='multidegree@example.com')

        self.assertTrue(UserDegree.objects.filter(user_student_id=user, degree=self.degree).exists())
        self.assertTrue(UserDegree.objects.filter(user_student_id=user, degree=degree2).exists())

class ProfileCustomizationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="Software Engineering",
            hours_needed=120,
            degree_type=1
        )
        self.register_url = reverse('register')
        self.profile_url = reverse('profile')
        self.update_profile_url = reverse('update_profile')

        self.user = User.objects.create_user(
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            password='StrongPass123!',
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )

    def test_user_information_update(self):
        self.client.login(email='testuser@example.com', password='StrongPass123!')
        
        data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updateduser@example.com',
        }
        
        response = self.client.post(self.update_profile_url, data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        
        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.last_name, 'UpdatedLast')
        self.assertEqual(self.user.email, 'updateduser@example.com')

    def test_valid_email_format(self):
        data = {
            'first_name': 'ValidEmail',
            'last_name': 'Test',
            'email': 'invalid-email',
        }
        self.client.login(email='testuser@example.com', password='StrongPass123!')
        response = self.client.post(self.update_profile_url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Enter a valid email address." in str(m) for m in messages))

    def test_duplicate_email_registration(self):
        User.objects.create_user(
            email='duplicate@example.com',
            first_name='Test',
            last_name='User',
            password='password123',
            is_student=True,
            is_advisor=False,
            student_id=999999999
        )

        data = {
            'email': 'duplicate@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'NewPass123!',
            'student_id': 123457091,
        }

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)

        self.assertRedirects(response, self.register_url)

        django_messages = list(response.wsgi_request._messages)
        self.assertTrue(any("This email is already registered." in str(m) for m in django_messages))
        self.assertEqual(User.objects.filter(email='duplicate@example.com').count(), 1)

    def test_degree_deletion(self):
        # Add a degree to the user profile first
        user_degree = UserDegree.objects.create(user_student_id=self.user, degree=self.degree)
        self.assertTrue(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree).exists())

        # Test degree deletion by selecting it
        data = {
            'current_degree': self.degree.id,
            'degree': '',
        }

        self.client.login(email='testuser@example.com', password='StrongPass123!')
        response = self.client.post(self.update_profile_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree).exists())

    def test_no_degree_selected_for_deletion(self):
        UserDegree.objects.create(user_student_id=self.user, degree=self.degree)

        # Ensure nothing is deleted if no degree is selected for removal
        data = {
            'current_degree': '',
            'degree': '',
        }

        self.client.login(email='testuser@example.com', password='StrongPass123!')
        response = self.client.post(self.update_profile_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree).exists())

    def test_add_degree_to_profile(self):
        # Add a new degree to the profile
        data = {
            'current_degree': '',
            'degree': self.degree.id,
        }

        self.client.login(email='testuser@example.com', password='StrongPass123!')
        response = self.client.post(self.update_profile_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree).exists())

    def test_degree_dropdown_loads_all_degrees(self):
        self.client.login(email='testuser@example.com', password='StrongPass123!')

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.degree.degree_name)

    def test_button_form_submission(self):
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'johndoe@example.com',
            'degree': self.degree.id,
        }

        self.client.login(email='testuser@example.com', password='StrongPass123!')
        response = self.client.post(self.update_profile_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.profile_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your profile has been updated." in str(m) for m in messages))

    def test_error_on_invalid_form_submission(self):
        data = {
            'first_name': '',
            'last_name': '',
            'email': 'invalid-email',
            'degree': '',
        }

        self.client.login(email='testuser@example.com', password='StrongPass123!')
        response = self.client.post(self.update_profile_url, data)
        self.assertEqual(response.status_code, 302)

        # Check for error messages
        django_messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Enter a valid email address." in str(m) for m in django_messages))

class LoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')
        self.home_url = reverse('home')

        # Create a test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='StrongPass123!',
            first_name='Test',
            last_name='User',
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )

    def test_successful_login(self):
        response = self.client.post(self.login_url, {
            'email': 'testuser@example.com',
            'password': 'StrongPass123!'
        })
        self.assertRedirects(response, self.home_url)

    def test_login_empty_fields_shows_error(self):
        login_url = reverse('login')

        response = self.client.post(login_url, {
            'email': '',
            'password': ''
        }, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any("required" in str(m).lower() for m in messages))

        response = self.client.post(login_url, {
            'email': '',
            'password': 'SomePassword123'
        }, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any("required" in str(m).lower() for m in messages))

        response = self.client.post(login_url, {
            'email': 'someone@example.com',
            'password': ''
        }, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any("required" in str(m).lower() for m in messages))

    def test_login_with_invalid_email_format(self):
        response = self.client.post(self.login_url, {
            'email': 'invalid-email',
            'password': 'somepassword'
        }, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertContains(response, "Invalid email or password")
        self.assertTrue(any("Invalid email or password" in str(m) for m in messages))