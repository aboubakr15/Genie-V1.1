# Generated by Django 5.0.7 on 2024-09-27 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_filterword'),
    ]

    operations = [
        migrations.CreateModel(
            name='FilterType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='filterword',
            name='filter_types',
            field=models.ManyToManyField(to='main.filtertype'),
        ),
    ]
