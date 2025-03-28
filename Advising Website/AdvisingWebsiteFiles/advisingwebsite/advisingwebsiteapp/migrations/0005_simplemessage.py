# Generated by Django 5.1.1 on 2025-03-02 08:35

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advisingwebsiteapp', '0004_user_student_id_userdegree'),
    ]

    operations = [
        migrations.CreateModel(
            name='SimpleMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author_messages', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
