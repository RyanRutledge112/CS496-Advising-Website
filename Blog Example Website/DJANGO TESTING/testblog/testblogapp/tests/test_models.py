from django.test import TestCase
from testblogapp.models import Category, Post, Comment
from django.contrib.auth.models import User

"""
Runs test cases for every single model function to make sure that the models are created
with their intended values.
"""

class TestModels(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')

        self.post = Post.objects.create(
            title='Test Post',
            title_tag='Test Tag',
            body='Test Body',
            author=self.user,
            category=self.category
        )

        self.comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            body='Testing the body'
        )

    def test_category_is_assigned_values_on_creation(self):
        self.assertEqual(self.category.name, 'Test Category')

    def test_post_is_assigned_values_on_creation(self):
        self.assertEqual(self.post.author, self.user)
        self.assertEqual(self.post.title, 'Test Post')
        self.assertEqual(self.post.title_tag, 'Test Tag')
        self.assertEqual(self.post.body, 'Test Body')
        self.assertEqual(str(self.post.category), self.category.name)

    def test_comment_is_assigned_values_on_creation(self):
        self.assertEqual(self.comment.post, self.post)
        self.assertEqual(self.comment.author, self.user)
        self.assertEqual(self.comment.body, 'Testing the body')

    def test_post_str_method(self):
        self.assertEqual(str(self.post), 'Test Post | testuser')

    def test_category_str_method(self):
        self.assertEqual(str(self.category), 'Test Category')

    def test_comment_str_method(self):
        self.assertEqual(str(self.comment), 'testuser - Testing the body')

    def test_post_get_absolute_url(self):
        self.assertEqual(self.post.get_absolute_url(), '/')

    def test_category_get_absolute_url(self):
        self.assertEqual(self.category.get_absolute_url(), '/')

    def test_comment_get_absolute_url(self):
        self.assertEqual(self.comment.get_absolute_url(), f'/article/{self.post.id}')