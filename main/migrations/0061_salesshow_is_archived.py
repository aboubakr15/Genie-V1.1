# Generated by Django 5.0.7 on 2024-11-06 19:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0060_salesteams_openers_closers'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesshow',
            name='is_archived',
            field=models.BooleanField(default=False),
        ),
    ]
