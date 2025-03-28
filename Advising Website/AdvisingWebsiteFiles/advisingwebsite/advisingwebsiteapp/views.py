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
from django.db import connection

from advisingwebsiteapp.models import User, Degree, UserDegree
from .scraptranscript import parse_transcript, store_user_degree
from .majorreqs import main as extract_major_requirements
from .majorreqs import get_user_major
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

        # Link the major degree to the user in UserDegree
        UserDegree.objects.create(user_student_id=user, degree=degree) 

        if minor:
            degree = Degree.objects.create(
                degree_name=minor,
                degree_number=minor_number,
                concentration=concentration,
                hours_needed=21,
                degree_type=2
            )
        # Link the minor degree to the user in UserDegree
        UserDegree.objects.create(user_student_id=user, degree=degree)

        if certificate:
            degree = Degree.objects.create(
                    degree_name=certificate,
                    degree_number=certificate_number,
                    concentration=certificate,
                    hours_needed=12,
                    degree_type=3
            )
        # Link the certificate degree to the user in UserDegree
        UserDegree.objects.create(user_student_id=user, degree=degree)

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
        print(f"DEBUG: Transcript processed: {processed_data}")

        store_user_degree(processed_data)

        # Get user's student_id and fetch major
        try:
            student_id = request.user.student_id 
        except AttributeError:
            return render(request, "uploadTranscript.html", {"error": "Student ID not found in user profile."})

        # Get major name
        major_name = get_user_major(student_id)

        if major_name:
            major_requirements = extract_major_requirements(student_id)
        else:
            # print("DEBUG: No major found for this student")
            major_requirements = None

        return render(request, "uploadTranscript.html", {
            "transcript_data": processed_data,
            "major_requirements": major_requirements
        })

    return render(request, 'uploadTranscript.html')

def profile(request):
    return render(request, 'profile.html')

@login_required
def update_profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        major = request.POST.get('major')
        major_number = request.POST.get('major_number')
        concentration = request.POST.get('concentration', '')
        minor = request.POST.get('minor', '')
        minor_number = request.POST.get('minor_number', '')
        certificate = request.POST.get('certificate', '')
        certificate_number = request.POST.get('certificate_number', '')

        #update only the fields that have been filled in
        if first_name:
            request.user.first_name = first_name
        if last_name:
            request.user.last_name = last_name
        if email:
            request.user.email = email
        request.user.save()
  
        # Call helper function to update degree information
        update_user_degrees(request)

        django_messages.success(request, 'Your profile has been updated.')
        return redirect('profile')
    return render(request, 'profile.html')

@login_required
def update_user_degrees(request):
    if request.method == 'POST':
        user = request.user  # Get logged-in user
        student_id = user.student_id  # Get student ID

        user_degrees = UserDegree.objects.filter(user_student_id=student_id)

        # Handle major
        major = request.POST.get('major')
        major_number = request.POST.get('major_number')
        
        if major:
            if not major_number:
                # If major is provided but major_number is missing, show error
                django_messages.error(request, "Please provide the major reference number.")
                return redirect('profile')
            
            # Fetch the existing minor degree record correctly
            old_major = UserDegree.objects.filter(user_student_id=user, degree__degree_type=1).first()

            if old_major:
                old_major.delete()
                connection.commit()

            # Create or update the new major
            major_degree, created = Degree.objects.get_or_create(degree_name=major, degree_number=major_number, degree_type=1, defaults={'hours_needed': 120})
            
            if major_number:
                major_degree.degree_number = major_number
                major_degree.save()

            # Add the new major degree to UserDegree
            new_major = UserDegree.objects.create(user_student_id=user, degree=major_degree)
            
        # Handle concentration
        concentration = request.POST.get('concentration', '')
        if concentration:
            # Check if the user has a major degree (degree_type=1)
            major_degree = user_degrees.filter(degree__degree_type=1).first()  # Get the existing major degree if it exists
            if major_degree:
                # Update concentration for the existing major degree
                major_degree.degree.concentration = concentration
                major_degree.degree.save()

        # Handle minor
        minor = request.POST.get('minor')
        minor_number = request.POST.get('minor_number')
        if minor:
            if not minor_number:
                # If minor is provided but minor_number is missing, show error
                django_messages.error(request, "Please provide the minor reference number.")
                return redirect('profile')
            
            # Fetch the existing minor degree record correctly
            old_minor = UserDegree.objects.filter(user_student_id=user, degree__degree_type=2).first()
            
            if old_minor:
                old_minor.delete()
                connection.commit()

            minor_degree, created = Degree.objects.get_or_create(degree_name=minor, degree_type=2, defaults={'hours_needed': 21})
            if minor_number:
                minor_degree.degree_number = minor_number
                minor_degree.save()

            # Add the new minor degree to UserDegree
            new_user_degree = UserDegree.objects.create(user_student_id=user, degree=minor_degree)
            
        # Handle certificate
        certificate = request.POST.get('certificate')
        certificate_number = request.POST.get('certificate_number')
        if certificate:
            if not certificate_number:
                # If certificate is provided but certificate_number is missing, show error
                messages.error(request, "Please provide the certificate reference number.")
                return redirect('profile')
            
            old_certificate = UserDegree.objects.filter(user_student_id=user, degree__degree_type=3).first()

            if old_certificate:
                print(f"Deleting old certificate: {old_certificate.degree.degree_name} (UserDegree ID: {old_certificate.id})")
                old_certificate.delete()
                connection.commit()

            certificate_degree, created = Degree.objects.get_or_create(degree_name=certificate, degree_type=3, defaults={'hours_needed': 12})
            if certificate_number:
                certificate_degree.degree_number = certificate_number
                certificate_degree.save()
                
            new_certificate = UserDegree.objects.create(user_student_id=user, degree=certificate_degree)
            
        return redirect('profile')

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