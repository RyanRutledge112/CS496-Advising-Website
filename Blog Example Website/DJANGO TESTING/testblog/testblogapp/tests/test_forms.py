from django.test import TestCase, Client
from testblogapp.forms import PostForm, EditForm, CommentForm, SearchForm
from django.contrib.auth.models import User
from testblogapp.models import Category, Post, Comment

"""
Runs test cases for every single form to make sure that the forms are only created
when all values are given. Tests are also ran to confirm that forms will not be created when
certain or all values are missing.
"""

class TestForms(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user,
            category=self.category.name
        )
    
    def test_post_form_valid_data(self):
        form = PostForm(data={
            'title': 'Test the title',
            'title_tag': 'Test the title tag',
            'category': 'Test Category',
            'body': 'Testing the body'
        })
        self.assertTrue(form.is_valid())
    
    def test_post_form_no_data(self):
        form = PostForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 4)

    def test_post_form_partial_data(self):
        form = PostForm(data={
            'title': 'Test the title',
            'body': 'Testing the body'
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 2)
    
    def test_edit_form_valid_data(self):
        form = EditForm(data={
            'title': 'Updated Title',
            'title_tag': 'Updated Tag',
            'body': 'Updated Body'
        })
        self.assertTrue(form.is_valid())
    
    def test_edit_form_no_data(self):
        form = EditForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 3)

    def test_comment_form_valid_data(self):
        form = CommentForm(data={
            'body': 'This is a test comment'
        })
        self.assertTrue(form.is_valid())

    def test_comment_form_no_data(self):
        form = CommentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)

    def test_search_form_valid_data(self):
        form = SearchForm(data={
            'query': 'Test search'
        })
        self.assertTrue(form.is_valid())

    def test_search_form_no_data(self):
        form = SearchForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)