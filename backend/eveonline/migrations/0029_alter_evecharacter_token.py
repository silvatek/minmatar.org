# Generated by Django 4.2.11 on 2024-04-09 12:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("esi", "0012_fix_token_type_choices"),
        ("eveonline", "0028_remove_evealliance_executor_corporation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="evecharacter",
            name="token",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="esi.token",
            ),
        ),
    ]
