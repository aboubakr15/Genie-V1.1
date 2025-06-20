# Generated by Django 5.0.7 on 2024-09-20 22:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0027_rename_is_cut_readyshow_is_done'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='salesshow',
            name='Agent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='salesshow',
            name='label',
            field=models.CharField(choices=[('EHUB', 'EHUB'), ('EHUB2', 'EHUB2'), ('EP', 'EP')], default='EHUB', max_length=5),
        ),
    ]
