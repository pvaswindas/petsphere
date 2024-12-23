# Generated by Django 5.1.3 on 2024-11-30 09:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Pet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('icon', models.ImageField(blank=True, null=True, upload_to='pet_type_icons/')),
            ],
        ),
        migrations.CreateModel(
            name='PetBreed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('icon', models.ImageField(blank=True, null=True, upload_to='pet_breed_icons/')),
                ('pet_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='breed', to='pets.pet')),
            ],
        ),
    ]
