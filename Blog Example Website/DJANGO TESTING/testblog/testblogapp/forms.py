from django import forms
from .models import Post, Category, Comment

#Creates the visual input boxes for the user to insert data into to create certain
#models in the database. Needed to create posts, comments, and categories.

choices = Category.objects.all().values_list('name', 'name')

choice_list = []

for item in choices:
    choice_list.append(item)

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'title_tag', 'category', 'body')

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'title_tag': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(choices=choice_list, attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control'}),

        }
    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['category'].widget = forms.Select(attrs={"class": 'form-control'}, choices=[(cat.name, cat.name) for cat in Category.objects.all()])

class EditForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'title_tag', 'body')

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'title_tag': forms.TextInput(attrs={'class': 'form-control'}),
           #'author': forms.Select(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={'class': 'form-control'}),
        }
    

class SearchForm(forms.Form):
    query = forms.CharField(label='Search', max_length=100)