from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def home(request):
    return render(request, 'home.html', {})

def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)  # Log in
            return redirect('home')  # Redirect to homepage
        else:
            messages.error(request, "Invalid email or password")  # Show error message
    return render(request, 'login.html')
