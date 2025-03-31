import json
from django.http import Http404, HttpResponseRedirect, HttpResponseServerError, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
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
        second_major = request.POST.get('second_major', '')
        second_major_number = request.POST.get('second_major_number', '')
        third_major = request.POST.get('third_major', '')
        third_major_number = request.POST.get('third_major_number', '')
        minor = request.POST.get('minor', '')
        minor_number = request.POST.get('minor_number', '')
        second_minor = request.POST.get('second_minor', '')
        second_minor_number = request.POST.get('second_minor_number', '')
        third_minor = request.POST.get('third_minor', '')
        third_minor_number = request.POST.get('third_minor_number', '')
        concentration = request.POST.get('concentration', '')
        second_concentration = request.POST.get('second_concentration', '')
        third_concentration = request.POST.get('third_concentration', '')
        certificate = request.POST.get('certificate', '')
        certificate_number = request.POST.get('certificate_number', '')
        second_certificate = request.POST.get('second_certificate', '')
        second_certificate_number = request.POST.get('second_certificate_number', '')
        third_certificate = request.POST.get('third_certificate', '')
        third_certificate_number = request.POST.get('third_certificate_number', '')

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

        # Create Degree record for the first major if it doesn't exist for this user
        degree, created = Degree.objects.get_or_create(
            degree_name=major,
            degree_number=major_number,
            concentration=concentration, 
            hours_needed=120,  
            degree_type=1  
        )

        # Link the major degree to the user in UserDegree only if it doesn't exist already
        if not UserDegree.objects.filter(user_student_id=user, degree=degree).exists():
            UserDegree.objects.create(user_student_id=user, degree=degree) 

        # Create Degree record for Second Major if provided
        if second_major:
            second_major_degree, created = Degree.objects.get_or_create(
                degree_name=second_major,
                degree_number=second_major_number,
                concentration=second_concentration,
                hours_needed=120,
                degree_type=1
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=second_major_degree).exists():
                UserDegree.objects.create(user_student_id=user, degree=second_major_degree)

        # Create Degree record for Third Major if provided
        if third_major:
            third_major_degree, created = Degree.objects.get_or_create(
                degree_name=third_major,
                degree_number=third_major_number,
                concentration=third_concentration,
                hours_needed=120,
                degree_type=1
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=third_major_degree).exists():
                 UserDegree.objects.create(user_student_id=user, degree=third_major_degree)

        if minor:
            minor_degree, created = Degree.objects.get_or_create(
                degree_name=minor,
                degree_number=minor_number,
                concentration=concentration,
                hours_needed=21,
                degree_type=2
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=minor_degree).exists():
                UserDegree.objects.create(user_student_id=user, degree=minor_degree)

        # Create Degree record for Second Minor if provided
        if second_minor:
            second_minor_degree, created = Degree.objects.get_or_create(
                degree_name=second_minor,
                degree_number=second_minor_number,
                concentration=concentration,
                hours_needed=21,
                degree_type=2
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=second_minor_degree).exists():
                UserDegree.objects.create(user_student_id=user, degree=second_minor_degree)

        # Create Degree record for Third minor if provided
        if third_minor:
            third_minor_degree, created = Degree.objects.get_or_create(
                degree_name=third_minor,
                degree_number=third_minor_number,
                concentration=concentration,
                hours_needed=21,
                degree_type=2
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=third_minor_degree).exists():
                 UserDegree.objects.create(user_student_id=user, degree=third_minor_degree)

        if certificate:
            certificate_degree, created = Degree.objects.get_or_create(
                degree_name=certificate,
                degree_number=certificate_number,
                concentration=certificate,
                hours_needed=12,
                degree_type=3
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=certificate_degree).exists():
                UserDegree.objects.create(user_student_id=user, degree=certificate_degree)

         # Create Degree record for Second certificate if provided
        if second_certificate:
            second_certificate_degree, created = Degree.objects.get_or_create(
                degree_name=second_certificate,
                degree_number=second_certificate_number,
                concentration=concentration,
                hours_needed=12,
                degree_type=3
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=second_certificate_degree).exists():
                UserDegree.objects.create(user_student_id=user, degree=second_certificate_degree)

        # Create Degree record for Third certificate if provided
        if third_certificate:
            third_certificate_degree, created = Degree.objects.get_or_create(
                degree_name=third_certificate,
                degree_number=third_certificate_number,
                concentration=concentration,
                hours_needed=12,
                degree_type=3
            )
            if not UserDegree.objects.filter(user_student_id=user, degree=third_certificate_degree).exists():
                 UserDegree.objects.create(user_student_id=user, degree=third_certificate_degree)

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
    user = request.user
    user_degrees = UserDegree.objects.filter(user_student_id=user).select_related('degree')

    # Separate degrees based on type
    majors = [ud.degree for ud in user_degrees if ud.degree.degree_type == 1]
    minors = [ud.degree for ud in user_degrees if ud.degree.degree_type == 2]
    certificates = [ud.degree for ud in user_degrees if ud.degree.degree_type == 3]

    # Get concentrations for majors and minors
    concentrations = {
        'major': [],
        'minor': []
    }

    for degree in user_degrees:
        concentration = degree.degree.concentration
        degree_type = degree.degree.degree_type
        degree_name = degree.degree.degree_name

        if concentration:
            if degree_type == 1:
                concentrations['major'].append({
                    'concentration': concentration,
                    'degree_name': degree_name,  # Store the degree name here
                    'degree': degree.degree
                })
            elif degree_type == 2:
                concentrations['minor'].append({
                    'concentration': concentration,
                    'degree_name': degree_name,  # Store the degree name here
                    'degree': degree.degree
                })

    context = {
        'user': user,
        'majors': majors,
        'minors': minors,
        'certificates': certificates,
        'concentrations': concentrations,
    }
    return render(request, 'profile.html', context)

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

        user_degrees = UserDegree.objects.filter(user_student_id=user)

        # Handle major
        major = request.POST.get('major')
        major_number = request.POST.get('major_number')
        selected_major_number = request.POST.get('selected_major')
        
        # Check if the major reference number is missing
        if major and not major_number:
            django_messages.error(request, "You must enter a Major Reference Number.")
            return redirect('profile') 

        # Handle major deletion
        if selected_major_number:
            print(f"Removing major with number: {selected_major_number}")  # Debugging
            major_degree = user_degrees.filter(degree__degree_number=selected_major_number, degree__degree_type=1).first()
            if major_degree:
                print(f"Deleting {major_degree.degree.degree_name} from UserDegree")
                major_degree.delete()
            else:
                print(f"No matching UserDegree found for major number {selected_major_number}")

        print(f"Received form data - New Major: {major}, Major Number: {major_number}")
        # Add the new major
        if major and major_number:
            print(f"Adding new major: {major} (Number: {major_number})")
            
            major_degree, created = Degree.objects.get_or_create(
                degree_number=major_number, 
                degree_type=1, 
                defaults={'degree_name': major, 'hours_needed': 120}
            )

            if created:
                print(f"Created new Degree entry: {major}")
            else:
                print(f"Degree already exists: {major}")

                if major_degree.degree_name != major:
                    major_degree.degree_name = major
                    major_degree.save()
                    print(f"Updated Degree name to: {major}")

            # Associate the new major with the user
            UserDegree.objects.create(user_student_id=user, degree=major_degree)
            print(f"Added {major} to UserDegree")

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
        selected_minor_number = request.POST.get('selected_minor')

        # Check if the minor reference number is missing
        if minor and not minor_number:
            django_messages.error(request, "You must enter a Minor Reference Number.")
            return redirect('profile') 

         # Handle minor deletion
        if selected_minor_number:
            print(f"Removing minor with number: {selected_minor_number}")  # Debugging
            minor_degree = user_degrees.filter(degree__degree_number=selected_minor_number, degree__degree_type=2).first()
            if minor_degree:
                print(f"Deleting {minor_degree.degree.degree_name} from UserDegree")
                minor_degree.delete()
            else:
                print(f"No matching UserDegree found for minor number {selected_minor_number}")

        print(f"Received form data - New Minor: {minor}, Minor Number: {minor_number}")
        # Add the new minor
        if minor and minor_number:
            print(f"Adding new minor: {minor} (Number: {minor_number})")
            
            minor_degree, created = Degree.objects.get_or_create(
                degree_number=minor_number, 
                degree_type=2, 
                defaults={'degree_name': minor, 'hours_needed': 21}
            )

            if created:
                print(f"Created new Degree entry: {minor}")
            else:
                print(f"Degree already exists: {minor}")

                if minor_degree.degree_name != minor:
                    minor_degree.degree_name = minor
                    minor_degree.save()
                    print(f"Updated Degree name to: {minor}")

            # Associate the new minor with the user
            UserDegree.objects.create(user_student_id=user, degree=minor_degree)
            print(f"Added {minor} to UserDegree")
            
        # Handle certificate
        certificate = request.POST.get('certificate')
        certificate_number = request.POST.get('certificate_number')
        selected_certificate_number = request.POST.get('selected_certificate')

        # Check if the certificate reference number is missing
        if certificate and not certificate_number:
            django_messages.error(request, "You must enter a Certificate Reference Number.")
            return redirect('profile') 

         # Handle certificate deletion
        if selected_certificate_number:
            print(f"Removing certificate with number: {selected_certificate_number}")  # Debugging
            certificate_degree = user_degrees.filter(degree__degree_number=selected_certificate_number, degree__degree_type=3).first()
            if certificate_degree:
                print(f"Deleting {certificate_degree.degree.degree_name} from UserDegree")
                certificate_degree.delete()
            else:
                print(f"No matching UserDegree found for certificate number {selected_certificate_number}")

        print(f"Received form data - New certificate: {certificate}, certificate Number: {certificate_number}")
        # Add the new certificate
        if certificate and certificate_number:
            print(f"Adding new certificate: {certificate} (Number: {certificate_number})")
            
            certificate_degree, created = Degree.objects.get_or_create(
                degree_number=certificate_number, 
                degree_type=3, 
                defaults={'degree_name': certificate, 'hours_needed': 12}
            )

            if created:
                print(f"Created new Degree entry: {certificate}")
            else:
                print(f"Degree already exists: {certificate}")

                if certificate_degree.degree_name != certificate:
                    certificate_degree.degree_name = certificate
                    certificate_degree.save()
                    print(f"Updated Degree name to: {certificate}")

            # Associate the new certificate with the user
            UserDegree.objects.create(user_student_id=user, degree=certificate_degree)
            print(f"Added {certificate} to UserDegree")
            
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
            "name": user_chat.chat.chat_name.replace(request.user.get_full_name(), "").strip(', ').replace(" ,", ""),
            "image_url": get_profile_picture(user_chat.chat.chat_name.replace(user.get_full_name(), "").strip(', ').replace(" ,", "")[0].lower()),
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
        "users": other_users,
        "full_name": mark_safe(json.dumps(request.user.get_full_name())),
        "profile_picture": get_profile_picture(user.get_short_name()[0].lower())
    })

@login_required
def room(request, chat_id):
    user = request.user
    chat = Chat.objects.filter(id=chat_id).first()
    if not chat:
        return HttpResponseRedirect(f"{reverse('error_page')}?exception={str('ERROR 404: Chat does not exist or could not be found.')}")
    if not ChatMember.objects.filter(user=user, chat=chat).first():
        return HttpResponseRedirect(f"{reverse('error_page')}?exception={str('ERROR 500: User is not a member of this chat.')}")
    user_chats = ChatMember.objects.filter(user=user).select_related("chat")
    other_users = User.objects.exclude(id=user.id)

    chats = [
        {
            "name": user_chat.chat.chat_name.replace(user.get_full_name(), "").strip(', ').replace(" ,", ""),
            "image_url": get_profile_picture(user_chat.chat.chat_name.replace(user.get_full_name(), "").strip(', ').replace(" ,", "")[0].lower()),
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
        "users": other_users,
        "full_name": mark_safe(json.dumps(request.user.get_full_name())),
        "profile_picture": get_profile_picture(user.get_short_name()[0].lower())
    })

@login_required
def check_chat_membership(request, chat_id):
    chat = Chat.objects.filter(id=chat_id).first()
    is_member = ChatMember.objects.filter(chat=chat, user=request.user).exists()
    return JsonResponse({'is_member': is_member})

def error_page(request):
    exception = request.GET.get('exception', 'An unknown error occurred.')
    return render(request, 'error.html', {'exception' : exception})

def get_profile_picture(letter):
        #Stored generic profile pictures
        pictures = {
            "a" : "https://static-00.iconduck.com/assets.00/a-letter-icon-512x512-j1mhihj0.png",
            "b" : "https://static-00.iconduck.com/assets.00/b-letter-icon-512x512-90rzacib.png",
            "c" : "https://static-00.iconduck.com/assets.00/c-letter-icon-512x512-6mbkqdec.png",
            "d" : "https://static-00.iconduck.com/assets.00/d-letter-icon-512x512-r9lvazse.png",
            "e" : "https://static-00.iconduck.com/assets.00/e-letter-icon-512x512-dt9oea54.png",
            "f" : "https://static-00.iconduck.com/assets.00/f-letter-icon-512x512-xg6ht0dr.png",
            "g" : "https://static-00.iconduck.com/assets.00/g-letter-icon-512x512-6pmz2jsc.png",
            "h" : "https://static-00.iconduck.com/assets.00/h-letter-icon-512x512-x6qbinvo.png",
            "i" : "https://static-00.iconduck.com/assets.00/i-letter-icon-512x512-dmvytbti.png",
            "j" : "https://static-00.iconduck.com/assets.00/j-letter-icon-512x512-x0xc0g9u.png",
            "k" : "https://static-00.iconduck.com/assets.00/k-letter-icon-512x512-7bxyhgb3.png",
            "l" : "https://static-00.iconduck.com/assets.00/l-letter-icon-512x512-y3zwxhv2.png",
            "m" : "https://static-00.iconduck.com/assets.00/m-letter-icon-512x512-dfiryt7g.png",
            "n" : "https://static-00.iconduck.com/assets.00/n-letter-icon-512x512-52nch8s7.png",
            "o" : "https://static-00.iconduck.com/assets.00/o-letter-icon-512x512-sj7vxh47.png",
            "p" : "https://static-00.iconduck.com/assets.00/p-letter-icon-512x512-h5sw1to6.png",
            "q" : "https://static-00.iconduck.com/assets.00/q-letter-icon-512x512-30ov2ad6.png",
            "r" : "https://static-00.iconduck.com/assets.00/r-letter-icon-512x512-l2j45l27.png",
            "s" : "https://static-00.iconduck.com/assets.00/s-letter-icon-512x512-a5ximws6.png",
            "t" : "https://static-00.iconduck.com/assets.00/t-letter-icon-512x512-bg5zozzy.png",
            "u" : "https://static-00.iconduck.com/assets.00/u-letter-icon-512x512-131g3vfy.png",
            "v" : "https://static-00.iconduck.com/assets.00/v-letter-icon-512x512-hjcawsh7.png",
            "w" : "https://static-00.iconduck.com/assets.00/w-letter-icon-512x512-1nemv88f.png",
            "x" : "https://static-00.iconduck.com/assets.00/x-letter-icon-512x512-3xx065ts.png",
            "y" : "https://static-00.iconduck.com/assets.00/y-letter-icon-512x512-ob5jvz98.png",
            "z" : "https://static-00.iconduck.com/assets.00/z-letter-icon-512x512-puk3v0kb.png"
        }
        profile_picture = pictures[letter]
        return profile_picture