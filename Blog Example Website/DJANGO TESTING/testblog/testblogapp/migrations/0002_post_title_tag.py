# Generated by Django 5.1.1 on 2024-09-23 22:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testblogapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='title_tag',
            field=models.CharField(default='Awesome Blog Website', max_length=255),
        ),
    ]
