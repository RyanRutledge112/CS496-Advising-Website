from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

#CREATED BY CHATGPT TO HELP WITH CREATION OF INITIAL CUSTOM SUPERUSER 2/14/2025
#https://chatgpt.com/share/67aedf9a-bd40-800c-88b0-05484d72365c
class Command(BaseCommand):
    help = 'Create a custom superuser for the application'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address of the superuser')
        parser.add_argument('--first_name', type=str, help='First name of the superuser')
        parser.add_argument('--last_name', type=str, help='Last name of the superuser')
        parser.add_argument('--password', type=str, help='Password of the superuser')

    def handle(self, *args, **options):
        email = options['email']
        first_name = options['first_name']
        last_name = options['last_name']
        password = options['password']

        #Check if any required arguments are missing
        if not email or not first_name or not last_name or not password:
            self.stdout.write(self.style.ERROR('Error: All fields are required'))
            return

        #Create the superuser
        try:
            User = get_user_model()
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.ERROR(f"User with email {email} already exists"))
                return

            user = User.objects.create_superuser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_student=False,
                is_advisor=False,
            )
            user.date_joined = timezone.now()
            user.save()

            self.stdout.write(self.style.SUCCESS(f'Superuser {email} created successfully'))

        except ValidationError as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred: {e}'))
