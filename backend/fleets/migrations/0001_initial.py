# Generated by Django 5.0.4 on 2024-04-20 02:34

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("eveonline", "0032_evecharacter_eveonline_e_charact_d47325_idx"),
        ("fittings", "0004_evefitting_ship_id"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EveFleetNotificationChannel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("discord_channel_id", models.BigIntegerField()),
                ("discord_channel_name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="EveFleet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("stratop", "Strategic Operation"),
                            ("non_strategic", "Non Strategic Operation"),
                            ("casual", "Casual Operation"),
                            ("training", "Training Operation"),
                        ],
                        max_length=32,
                    ),
                ),
                ("start_time", models.DateTimeField()),
                ("location", models.CharField(blank=True, max_length=255)),
                (
                    "audience",
                    models.ManyToManyField(blank=True, to="auth.group"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "doctrine",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="fittings.evedoctrine",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EveFleetInstance",
            fields=[
                (
                    "id",
                    models.BigIntegerField(primary_key=True, serialize=False),
                ),
                ("start_time", models.DateTimeField(auto_now_add=True)),
                ("end_time", models.DateTimeField(blank=True, null=True)),
                ("is_free_move", models.BooleanField(default=False)),
                ("is_registered", models.BooleanField(default=False)),
                ("motd", models.TextField(blank=True)),
                (
                    "eve_fleet",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="fleets.evefleet",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EveFleetInstanceMember",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("join_time", models.DateTimeField(auto_now_add=True)),
                ("role", models.CharField(max_length=255)),
                ("role_name", models.CharField(max_length=255)),
                ("ship_type_id", models.BigIntegerField()),
                ("solar_system_id", models.BigIntegerField()),
                ("squad_id", models.IntegerField()),
                ("station_id", models.BigIntegerField(blank=True, null=True)),
                ("takes_fleet_warp", models.BooleanField(default=False)),
                ("wing_id", models.IntegerField()),
                (
                    "character",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "eve_fleet_instance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="fleets.evefleetinstance",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EveFleetNotification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("preping", "Preping"), ("ping", "Ping")],
                        max_length=10,
                    ),
                ),
                (
                    "fleet",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="fleets.evefleet",
                    ),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="fleets.evefleetnotificationchannel",
                    ),
                ),
            ],
            options={
                "unique_together": {("type", "fleet")},
            },
        ),
    ]
