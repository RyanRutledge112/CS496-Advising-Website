from django.test import SimpleTestCase
from django.urls import reverse, resolve
from testblogapp import views

#Checking all urls to make sure that they are showing the correct views and are functioning as intended.

class TestUrls(SimpleTestCase):
    def test_home_url_resolves(self):
        url = reverse("home")
        self.assertEqual(resolve(url).func.view_class, views.HomeView)
    
    def test_article_detail_url_resolves(self):
        url = reverse("article-details", args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ArticleDetailView)
    
    def test_add_post_url_resolves(self):
        url = reverse("add_post")
        self.assertEqual(resolve(url).func.view_class, views.AddPostView)

    def test_update_post_url_resolves(self):
        url = reverse("update_post", args=[1])
        self.assertEqual(resolve(url).func.view_class, views.UpdatePostView)
    
    def test_delete_post_url_resolves(self):
        url = reverse("delete_post", args=[1])
        self.assertEqual(resolve(url).func.view_class, views.DeletePostView)
    
    def test_add_category_url_resolves(self):
        url = reverse("add_category")
        self.assertEqual(resolve(url).func.view_class, views.AddCategoryView)

    def test_category_url_resolves(self):
        url = reverse("category", args=["Calculus"])
        self.assertEqual(resolve(url).func, views.CategoryView)

    def test_add_comment_url_resolves(self):
        url = reverse("add_comment", args=[1])
        self.assertEqual(resolve(url).func.view_class, views.AddCommentView)
    
    def test_edit_comment_url_resolves(self):
        url = reverse("edit_comment", args=[1])
        self.assertEqual(resolve(url).func.view_class, views.EditCommentView)
    
    def test_delete_comment_url_resolves(self):
        url = reverse("delete_comment", args=[1])
        self.assertEqual(resolve(url).func.view_class, views.DeleteCommentView)