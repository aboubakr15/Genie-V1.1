# Generated by Django 5.1.3 on 2024-11-30 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0064_sheet_is_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='readyshow',
            name='is_archived',
            field=models.BooleanField(default=False),
        ),
    ]
