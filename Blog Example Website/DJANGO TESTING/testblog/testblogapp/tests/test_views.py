from django.test import TestCase, Client
from django.urls import reverse
from testblogapp.models import Category, Post, Comment
from django.contrib.auth.models import User

"""
Runs a test on every single view in the website and confirms that they are functioning as intended.
Will show failures if a template doesn't load, a link does not work, or if the page opened was not
the one that was intended to be loaded.
"""


class TestHomeView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user,
            category=self.category
        )
        self.url = reverse('home')

    def test_home_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, self.post.title)


class TestArticleDetailView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user,
            category=self.category
        )
        self.url = reverse('article-details', args=[self.post.id])

    def test_article_detail_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'article_details.html')
        self.assertContains(response, self.post.title)


class TestAddPostView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.url = reverse('add_post')

    def test_add_post_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_post.html')

    def test_add_post_form_submission(self):
        response = self.client.post(self.url, {
            'title': 'Test New Post',
            'title_tag': 'Test New Tag',
            'body': 'Testing the body',
            'category': self.category.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.filter(title='Test New Post').exists())


class TestAddCategoryView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        self.url = reverse('add_category')

    def test_add_category_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_category.html')

    def test_add_category_form_submission(self):
        response = self.client.post(self.url, {'name': 'New Category'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='New Category').exists())


class TestUpdatePostView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.post = Post.objects.create(
            title='Old Post',
            title_tag='Old Tag',
            body='Testing the old body',
            author=self.user,
            category=self.category
        )
        self.url = reverse('update_post', args=[self.post.id])
        self.client.login(username='testuser', password='password')

    def test_update_post_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'update_post.html')

    def test_update_post_form_submission(self):
        response = self.client.post(self.url, {
            'title': 'Updated Post',
            'title_tag': 'Updated Tag',
            'body': 'Testing the updated body',
            'category': self.category.id
        })
        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'Updated Post')


class TestDeletePostView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user,
            category=self.category
        )
        self.url = reverse('delete_post', args=[self.post.id])
        self.client.login(username='testuser', password='password')

    def test_delete_post_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'delete_post.html')

    def test_delete_post_submission(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())


class TestCategoryView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user,
            category=self.category
        )
        self.url = reverse('category', args=['Test-Category'])

    def test_category_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories.html')
        self.assertContains(response, self.post.title)


class TestAddCommentView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user
        )
        self.url = reverse('add_comment', args=[self.post.id])
        self.client.login(username='testuser', password='password')

    def test_add_comment_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_comment.html')

    def test_add_comment_form_submission(self):
        response = self.client.post(self.url, {'body': 'Test Comment'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(body='Test Comment').exists())


class TestEditCommentView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user
        )
        self.comment = Comment.objects.create(
            body='Original Comment',
            post=self.post,
            author=self.user
        )
        self.url = reverse('edit_comment', args=[self.comment.id])
        self.client.login(username='testuser', password='password')

    def test_edit_comment_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_comment.html')

    def test_edit_comment_form_submission(self):
        response = self.client.post(self.url, {'body': 'Updated Comment'})
        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.body, 'Updated Comment')


class TestDeleteCommentView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.post = Post.objects.create(
            title='Test the post',
            title_tag='Test the tag',
            body='Testing the body',
            author=self.user
        )
        self.comment = Comment.objects.create(
            body='Test Comment',
            post=self.post,
            author=self.user
        )
        self.url = reverse('delete_comment', args=[self.comment.id])
        self.client.login(username='testuser', password='password')

    def test_delete_comment_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'delete_comment.html')

    def test_delete_comment_submission(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())