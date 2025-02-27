from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from .models import Chat, ChatMember, Message
from django.contrib.auth.forms import PasswordChangeForm

from advisingwebsiteapp.models import User
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
            django_messages.error(request, "Invalid email or password")  # Show error message
    return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Set default values for is_student and is_advisor
        is_student = True  # Default to True (most users are students)
        is_advisor = False  # Default to False (most users are not advisors)

        # Check if the user already exists
        if User.objects.filter(email=email).exists():
            django_messages.error(request, "This email is already registered.")
            return redirect('register')

        # Create a new user
        user = User.objects.create_user(email=email, first_name=first_name, 
                                        last_name=last_name, password=password,
                                        is_student=is_student, is_advisor=is_advisor)
        user.save()

        # Log the user in after registration
        login(request, user)
        return redirect('home')  # Redirect to home after successful registration

    return render(request, 'register.html')

@login_required
def messages_page(request):
    # Get all chats where the user is a member
    user_chats = Chat.objects.filter(chatmember__user=request.user)

    # Get latest message and unread count for each conversation
    conversations = []
    for chat in user_chats:
        last_message = Message.objects.filter(chat=chat).order_by('-date_sent').first()

        # Get user's chat member record
        chat_member = ChatMember.objects.get(chat=chat, user=request.user)

        # Count unread messages (messages sent after user last viewed)
        unread_count = Message.objects.filter(chat=chat, date_sent__gt=chat_member.chat_last_viewed).count()

        conversations.append({
            'chat': chat,
            'last_message': last_message.message_content if last_message else "No messages yet.",
            'unread_count': unread_count,
        })

    return render(request, 'messages.html', {
        'conversations': conversations
    })

@login_required
def send_message(request):
    if request.method == "POST":
        chat_id = request.POST.get('chat_id')
        message_content = request.POST.get('message_content')

        chat = Chat.objects.get(id=chat_id)
        chat_member = ChatMember.objects.get(chat=chat, user=request.user)

        Message.objects.create(
            chat=chat,
            sent_by_member=chat_member,
            message_content=message_content
        )

        # Update the chat last viewed
        chat_member.chat_last_viewed = timezone.now()
        chat_member.save()

    return redirect('messages')

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

def profile(request):
    return render(request, 'profile.html')

@login_required
def update_profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        #update only the fields that have been filled in
        if first_name:
            request.user.first_name = first_name
        if last_name:
            request.user.last_name = last_name
        if email:
            request.user.email = email

        request.user.save()
        django_messages.success(request, 'Your profile has been updated.')
        return redirect('profile')
    return render(request, 'profile.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')  # Get the old password from the form
        form = PasswordChangeForm(request.user, request.POST)

        # Check if the old password is correct
        if not request.user.check_password(old_password):
            django_messages.error(request, 'Your old password is incorrect.')
            return render(request, 'changePassword.html', {'form': form})

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            django_messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            django_messages.error(request, 'Unable to update password. Try again!')
            return render(request, 'changePassword.html', {'form': form})
    else:
        form = PasswordChangeForm(request.user)
        return render(request, 'changePassword.html', {'form': form})