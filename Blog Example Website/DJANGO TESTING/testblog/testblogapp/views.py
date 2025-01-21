from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Post, Category, Comment
from .forms import PostForm, EditForm, CommentForm
from django.urls import reverse_lazy

#Creates the views that will be inserted into the website. Views can be interacted with
#and changed by the user, and some views will redirect to other parts of the website
#after being changed or interacted with.


#def home(request):
    #return render(request, 'home.html', {})

class HomeView(ListView):
    model = Post
    template_name = 'home.html'

    def get_context_data(self, *args, **kwargs):
        cat_menu = Category.objects.all()
        context = super(HomeView, self).get_context_data(*args, **kwargs)
        context['cat_menu'] = cat_menu
        
        # Handle search query
        query = self.request.GET.get('query', '')
        context['query'] = query  # Pass the query to the template
        context['post_list'] = []  # Initialize as an empty list

        if query:
            context['post_list'] = Post.objects.filter(body__icontains=query).order_by('-post_date')  # Search by body
        else:
            context['post_list'] = Post.objects.all().order_by('-post_date')
        return context
    

class ArticleDetailView(DetailView):
    model = Post
    template_name = 'article_details.html'

    def get_context_data(self, *args, **kwargs):
        cat_menu = Category.objects.all()
        context = super(ArticleDetailView, self).get_context_data(*args, **kwargs)
        context['cat_menu'] = cat_menu  
        return context

class AddPostView(CreateView):
    model = Post
    form_class = PostForm
    template_name = 'add_post.html'
    #fields = '__all__'
    #fields = ('title', 'body')a

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        cat_menu = Category.objects.all()
        context = super(AddPostView, self).get_context_data(*args, **kwargs)
        context['cat_menu'] = cat_menu  
        return context
    
class AddCategoryView(CreateView):
    model = Category
    template_name = 'add_category.html'
    fields = '__all__'

    def get_context_data(self, *args, **kwargs):
        cat_menu = Category.objects.all()
        context = super(AddCategoryView, self).get_context_data(*args, **kwargs)
        context['cat_menu'] = cat_menu  
        return context
    
class UpdatePostView(UpdateView):
    model = Post
    form_class = EditForm
    template_name = 'update_post.html'
    #fields = ['title', 'title_tag', 'body']

    def get_context_data(self, *args, **kwargs):
        cat_menu = Category.objects.all()
        context = super(UpdatePostView, self).get_context_data(*args, **kwargs)
        context['cat_menu'] = cat_menu  
        return context
    
class DeletePostView(DeleteView):
    model = Post
    template_name = 'delete_post.html'
    success_url = reverse_lazy('home')

    def get_context_data(self, *args, **kwargs):
        cat_menu = Category.objects.all()
        context = super(DeletePostView, self).get_context_data(*args, **kwargs)
        context['cat_menu'] = cat_menu  
        return context
    
from django.db.models import Q

def CategoryView(request, cats):
    category_posts = Post.objects.filter(category__iexact=cats.replace('-', ' '))
    cat_menu = Category.objects.all()  # Retrieve all categories for the menu
    context = {
        'cats': cats.title().replace('-', ' '),
        'category_posts': category_posts,
        'cat_menu': cat_menu  # Include cat_menu in context
    }
    return render(request, 'categories.html', context)
   

class AddCommentView(CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'add_comment.html'

    def form_valid(self, form):
        form.instance.post_id = self.kwargs['pk']
        form.instance.author = self.request.user
        return super().form_valid(form)

class EditCommentView(UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'edit_comment.html'

class DeleteCommentView(DeleteView):
    model = Comment
    template_name = 'delete_comment.html'

    def get_success_url(self):
        return reverse_lazy('article-details', kwargs={'pk': self.object.post.pk})
    
