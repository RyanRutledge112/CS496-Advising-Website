from django.shortcuts import render, redirect
from .models import Post
from django.contrib.auth.decorators import login_required

# View to display the feed
def feed(request):
    posts = Post.objects.all().order_by('-created_at')  # Get posts sorted by newest first
    return render(request, 'feed.html', {'posts': posts})

# View to handle post creation
@login_required
def create_post(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')
        post = Post.objects.create(user=request.user, content=content, image=image)
        return redirect('feed')