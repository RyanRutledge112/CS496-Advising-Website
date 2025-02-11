from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .scraptranscript import parse_transcript
import os

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

def register(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if the user already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return redirect('register')

        # Create a new user
        user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name)
        user.save()

        # Log the user in after registration
        login(request, user)
        return redirect('home')  # Redirect to home after successful registration

    return render(request, 'register.html')

def features(request):
    return render(request, 'features.html')
    
def messages(request):
    return render(request, 'messages.html')

def upload_transcript(request):
    if request.method == "POST" and request.FILES.get("pdfFile"):
        uploaded_file = request.FILES["pdfFile"]
        credit_hours = request.POST.get("inputCreditHours", "15")
        file_path = f"uploads/{uploaded_file.name}"

        os.makedirs("uploads", exist_ok=True)

        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        processed_data = parse_transcript(file_path)

        return render(request, "uploadTranscript.html", {"data": processed_data})

    return render(request, 'uploadTranscript.html')