# Generated by Django 3.2 on 2021-04-13 11:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('financemarker', '0006_rename_parsed_insider_tg_messaged'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fm_id', models.CharField(max_length=30, unique=True, verbose_name='financemarker ID')),
                ('title', models.CharField(max_length=20, null=True, verbose_name='Заголовок')),
                ('content', models.TextField(null=True, verbose_name='Текст')),
                ('link', models.CharField(max_length=50, null=True, verbose_name='Ссылка')),
                ('publicated', models.DateTimeField(verbose_name='Время и дата публикации')),
                ('insider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='financemarker.insider', verbose_name='Инсайдер')),
            ],
            options={
                'verbose_name': 'Новость',
                'verbose_name_plural': 'Новости',
            },
        ),
    ]