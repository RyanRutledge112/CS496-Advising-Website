# Generated by Django 5.2 on 2025-04-14 03:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advisingwebsiteapp', '0011_course_corequisites_course_recent_terms_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='prerequisites',
            name='group_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
