from django.test import TestCase, Client
from django.urls import reverse
from advisingwebsiteapp.models import User, Degree, UserDegree
from django.utils.translation import activate

class AccountCreationIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.degree1 = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="AI",
            hours_needed=120,
            degree_type=1
        )
        self.degree2 = Degree.objects.create(
            degree_name="Data Science",
            degree_number="DS201",
            concentration="Big Data",
            hours_needed=120,
            degree_type=1
        )
        self.register_url = reverse('register')

    def test_registration_success_flow(self):
       
        response = self.client.post(self.register_url, {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@example.com',
            'password': 'Password123!',
            'student_id': '987654321',
            'degrees[]': [str(self.degree1.id)],
        })
        self.assertRedirects(response, reverse('home'))

        user = User.objects.get(email='alice@example.com')
        self.assertTrue(UserDegree.objects.filter(user_student_id=user, degree=self.degree1).exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_duplicate_email_prevention(self):
        
        User.objects.create_user(
            email='duplicate@example.com',
            first_name='Dupe',
            last_name='User',
            password='Password123!',
            is_student=True,
            is_advisor=False,
            student_id='123456789'
        )
        response = self.client.post(self.register_url, {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'duplicate@example.com',
            'password': 'Password123!',
            'student_id': '111222333',
            'degrees[]': [str(self.degree1.id)],
        })
        self.assertRedirects(response, self.register_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("email is already registered" in str(m).lower() for m in messages))

    def test_duplicate_student_id_prevention(self):
       
        User.objects.create_user(
            email='student1@example.com',
            first_name='Stu',
            last_name='Dent',
            password='Password123!',
            is_student=True,
            is_advisor=False,
            student_id='555666777'
        )
        response = self.client.post(self.register_url, {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'student2@example.com',
            'password': 'Password123!',
            'student_id': '555666777',
            'degrees[]': [str(self.degree1.id)],
        })
        self.assertRedirects(response, self.register_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("student id is already registered" in str(m).lower() for m in messages))

    def test_multiple_degree_selection(self):
        
        response = self.client.post(self.register_url, {
            'first_name': 'Bob',
            'last_name': 'DegreeGuy',
            'email': 'bob@example.com',
            'password': 'GreatPass123!',
            'student_id': '777888999',
            'degrees[]': [str(self.degree1.id), str(self.degree2.id)],
        })
        self.assertRedirects(response, reverse('home'))

        user = User.objects.get(email='bob@example.com')
        degrees = UserDegree.objects.filter(user_student_id=user)
        self.assertEqual(degrees.count(), 2)

    def test_all_degrees_loaded_in_registration_form(self):
        activate('en')
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.degree1.degree_name)
        self.assertContains(response, self.degree2.degree_name)

class ProfileCustomizationIntegrationTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='StrongPass123!',
            first_name='Test',
            last_name='User',
            is_student=True,
            is_advisor=False
        )
        
        self.client.login(email='testuser@example.com', password='StrongPass123!')

        self.degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="AI",
            hours_needed=120,
            degree_type=1
        )

        self.profile_url = reverse('profile')
        self.update_profile_url = reverse('update_profile')

    def test_profile_update_reflected_on_profile_page(self):
        self.client.login(email='testuser@example.com', password='StrongPass123!')
        
        data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updatedemail@example.com'
        }

        response = self.client.post(self.update_profile_url, data, follow=True)

        self.user.refresh_from_db()

        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.last_name, 'UpdatedLast')
        self.assertEqual(self.user.email, 'updatedemail@example.com')

        self.assertContains(response, "UpdatedFirst")
        self.assertContains(response, "UpdatedLast")
    
    def test_degree_addition_and_dropdown_reflects_change(self):
        self.client.login(email='testuser@example.com', password='StrongPass123!')

        data = {
            'current_degree': '',
            'degree': self.degree.id
        }

        response = self.client.post(self.update_profile_url, data, follow=True)
        self.assertTrue(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree).exists())

        self.assertContains(response, self.degree.degree_name)

    def test_degree_deletion_reflected_in_dropdown(self):
        UserDegree.objects.create(user_student_id=self.user, degree=self.degree)
        self.client.login(email='testuser@example.com', password='StrongPass123!')

        data = {
            'current_degree': self.degree.id,
            'degree': ''
        }

        response = self.client.post(self.update_profile_url, data, follow=True)
        self.assertFalse(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree).exists())

        # Check it’s removed from the user’s degree dropdown
        self.assertNotContains(response, f'<option value="{self.degree.id}">{self.degree.degree_name}', html=True)

    def test_changes_after_update_button_clicked(self):
        self.client.login(email='testuser@example.com', password='StrongPass123!')

        response = self.client.get(self.profile_url)
        self.user.refresh_from_db()

        self.assertEqual(self.user.first_name, 'Test')
        self.assertNotContains(response, "UpdatedFirst")

        #submit the update form
        update_data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updateduser@example.com'
        }

        response = self.client.post(self.update_profile_url, update_data, follow=True)
        self.user.refresh_from_db()

        # Ensure changes are made after form submission
        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertContains(response, 'UpdatedFirst')
    
    def test_all_degrees_loaded_and_single_selection(self):
        degree2 = Degree.objects.create(
            degree_name="Data Science",
            degree_number="DS201",
            concentration="Big Data",
            hours_needed=120,
            degree_type=1
        )

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.degree.degree_name)
        self.assertContains(response, degree2.degree_name)

        self.assertContains(response, '<select', count=2)
        self.assertNotContains(response, 'multiple')

class Login(TestCase):
    def test_successful_login_redirects_to_home(self):
        login_url = reverse('login')
        User.objects.create_user(
            email='loginuser@example.com',
            first_name='Login',
            last_name='User',
            password='TestPassword123!',
            student_id='000111222',
            is_student=True,
            is_advisor=False
        )
        response = self.client.post(login_url, {
            'email': 'loginuser@example.com',
            'password': 'TestPassword123!'
        })
        self.assertRedirects(response, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_invalid_credentials_shows_error(self):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            'email': 'nonexistent@example.com',
            'password': 'WrongPass123!'
        }, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any("invalid email or password" in str(m).lower() for m in messages))

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
