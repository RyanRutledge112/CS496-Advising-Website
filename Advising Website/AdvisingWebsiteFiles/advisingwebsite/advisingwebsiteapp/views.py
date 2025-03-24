import json
from django.http import Http404, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from .models import Chat, ChatMember, Message
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.safestring import mark_safe

from advisingwebsiteapp.models import User, Degree
from .scraptranscript import parse_transcript
import os
import re

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
        student_id = request.POST.get('student_id')
        major = request.POST.get('major')
        major_number = request.POST.get('major_number')
        minor = request.POST.get('minor', '')
        minor_number = request.POST.get('minor_number', '')
        concentration = request.POST.get('concentration', '')
        certificate = request.POST.get('certificate', '')
        certificate_number = request.POST.get('certificate_number', '')

        # Set default values for is_student and is_advisor
        is_student = True  # Default to True (most users are students)
        is_advisor = False  # Default to False (most users are not advisors)

        # Password validation
        password_regex = re.compile(r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{9,}$')
        if not password_regex.match(password):
            django_messages.error(request, "Password must be at least 9 characters long, include an uppercase letter, "
            "a number, and a special character.")
            return redirect('register')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            django_messages.error(request, "This email is already registered.")
            return redirect('register')
        
        #check if student_id already exists
        if User.objects.filter(student_id=student_id).exists():
            django_messages.error(request, "This student id is already registered.")
            return redirect('register')

        # Create a new user
        user = User.objects.create_user(email=email, first_name=first_name, 
                                        last_name=last_name, password=password,
                                        is_student=is_student, is_advisor=is_advisor,
                                        student_id=student_id)
        user.save()

        # Create Degree record 
        degree = Degree.objects.create(
            degree_name=major,
            degree_number=major_number,
            concentration=concentration, 
            hours_needed=120,  
            degree_type=1  
        ) 

        if minor:
            degree = Degree.objects.create(
                degree_name=minor,
                degree_number=minor_number,
                concentration=concentration,
                hours_needed=21,
                degree_type=2
            )

        if certificate:
            degree = Degree.objects.create(
                    degree_name=certificate,
                    degree_number=certificate_number,
                    concentration=certificate,
                    hours_needed=12,
                    degree_type=3
            )
        degree.save()

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

@login_required
def chathome(request):
    user = request.user
    user_chats = ChatMember.objects.filter(user=user).select_related("chat")
    other_users = User.objects.exclude(id=user.id)

    chats = [
        {
            "name": user_chat.chat.chat_name,
            "image_url": "http://emilcarlsson.se/assets/louislitt.png",
            "members": list(User.objects.filter(joined_chats__chat=user_chat.chat).values_list("id", flat=True)),
            "chat_id": user_chat.chat.id,
            "last_message": user_chat.chat.chat_messages.order_by('-date_sent').first().message_content
            if user_chat.chat.chat_messages.exists() else "No messages yet."
        }
        for user_chat in user_chats
    ]

    return render(request, 'chat/room_base.html', {
        "chats": chats, 
        "email": mark_safe(json.dumps(request.user.email)), 
        "users": other_users
    })

@login_required
def room(request, chat_id):
    user = request.user
    chat = get_object_or_404(Chat, id=chat_id)
    if not ChatMember.objects.filter(user=user, chat=chat).exists():
        return redirect('error_page')
    user_chats = ChatMember.objects.filter(user=user).select_related("chat")
    other_users = User.objects.exclude(id=user.id)

    chats = [
        {
            "name": user_chat.chat.chat_name,
            "image_url": "http://emilcarlsson.se/assets/louislitt.png",
            "members": list(User.objects.filter(joined_chats__chat=user_chat.chat).values_list("id", flat=True)),
            "chat_id": user_chat.chat.id,
            "last_message": user_chat.chat.chat_messages.order_by('-date_sent').first().message_content
            if user_chat.chat.chat_messages.exists() else "No messages yet.",
        }
        for user_chat in user_chats
    ]
    
    return render(request, "chat/room.html", {
        'chat_id': chat_id,
        "email": mark_safe(json.dumps(request.user.email)),
        "chats": chats,
        "users": other_users
    })

@login_required
def check_chat_membership(request, chat_id):
    chat = Chat.objects.filter(id=chat_id).first()
    is_member = ChatMember.objects.filter(chat=chat, user=request.user).exists()
    return JsonResponse({'is_member': is_member})

def error_page(request, exception=None):
    return render(request, 'error.html', status=500)