# Generated by Django 5.1.2 on 2025-05-23 22:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("freight", "0005_evefreightroute_destination_location_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="evefreightroute",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="evefreightroute",
            name="destination",
            field=models.ForeignKey(
                help_text="Deprecated, use destination_location",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="destination",
                to="freight.evefreightlocation",
            ),
        ),
        migrations.AlterField(
            model_name="evefreightroute",
            name="orgin",
            field=models.ForeignKey(
                help_text="Deprecated, use origin_location",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="orgin",
                to="freight.evefreightlocation",
            ),
        ),
    ]
