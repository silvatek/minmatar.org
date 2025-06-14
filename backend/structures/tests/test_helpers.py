import unittest
import factory
from datetime import datetime, timezone

from django.db.models import signals

from esi.models import Token, Scope
from eveonline.models import EveCorporation, EveCharacter
from structures.models import EveStructurePing
from structures.helpers import (
    get_skyhook_details,
    get_structure_details,
    get_notification_characters,
    parse_structure_notification,
    is_new_event,
    StructureResponse,
)


def make_character(char_id, corp, scopes) -> EveCharacter:
    char = EveCharacter.objects.create(
        character_id=char_id,
        character_name=f"Pilot {char_id}",
        corporation=corp,
        token=Token.objects.create(
            character_id=char_id,
        ),
    )
    for scope_name in scopes:
        char.token.scopes.add(
            Scope.objects.get_or_create(
                name=scope_name,
            )[0]
        )
    char.token.save()
    return char


class StructureHelperTest(unittest.TestCase):

    def test_get_skyhook_details(self):
        selected_item_window = "Orbital Skyhook (KBP7-G III) [Sukanan Inititive]\n0.5 AU\nReinforced until 2024.07.17 11:10:47"
        expected = StructureResponse(
            structure_name="Orbital Skyhook",
            location="KBP7-G III",
            # "owner": "Sukanan Inititive",
            timer=datetime.strptime(
                "2024.07.17 11:10:47", "%Y.%m.%d %H:%M:%S"
            ),
        )
        self.assertEqual(get_skyhook_details(selected_item_window), expected)

    def test_get_structure_details(self):
        selected_item_window = (
            "Sosala - WATERMELLON\n0 m\nReinforced until 2024.06.23 23:20:58"
        )
        expected = StructureResponse(
            location="Sosala",
            structure_name="WATERMELLON",
            timer=datetime.strptime(
                "2024.06.23 23:20:58", "%Y.%m.%d %H:%M:%S"
            ),
        )
        self.assertEqual(get_structure_details(selected_item_window), expected)

    def test_anchoring_structure(self):
        selected_item_window = (
            "Sosala - WATERMELLON\n0 m\nAnchoring until 2024.06.23 23:20:58"
        )
        expected = StructureResponse(
            location="Sosala",
            structure_name="WATERMELLON",
            timer=datetime.strptime(
                "2024.06.23 23:20:58", "%Y.%m.%d %H:%M:%S"
            ),
        )
        self.assertEqual(get_structure_details(selected_item_window), expected)

    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def test_get_notification_characters(self):
        scopes = [
            "esi-characters.read_notifications.v1",
            "esi-fleets.read_fleet.v1",
        ]
        corp = EveCorporation.objects.create(
            corporation_id=1001,
            name="MegaCorp",
        )
        make_character(2001, corp, scopes)
        make_character(2002, corp, [])
        make_character(2003, corp, scopes)
        make_character(2004, corp, scopes)
        make_character(2005, None, scopes)

        chars = get_notification_characters(corp.id)

        self.assertEqual(3, chars.count())

    def test_parse_notification(self):
        text = """
            solarsystemID: 30002538
            structureID: &id001 1049253339308
            structureShowInfoData:
             - showinfo
             - 35826
             - *id001
            structureTypeID: 35826
            timeLeft: 1670149438753
            timestamp: 133926971500000000
            vulnerableTime: 9000000000
        """

        data = parse_structure_notification(text)
        self.assertEqual(1049253339308, data["structure_id"])

    def test_should_ping(self):
        event = EveStructurePing.objects.create(
            notification_id=10000,
            notification_type="Test",
            summary="ABC",
            event_time=datetime(2025, 1, 1, 21, 30, 0, 0, tzinfo=timezone.utc),
        )
        now = datetime(2025, 1, 1, 23, 50, 0, 0, tzinfo=timezone.utc)

        self.assertFalse(is_new_event(event, now))

        now = datetime(2025, 1, 1, 21, 30, 0, 0, tzinfo=timezone.utc)

        self.assertTrue(is_new_event(event, now))

        EveStructurePing.objects.create(
            notification_id=10001,
            notification_type="Test",
            summary="ABC",
            event_time=datetime(2025, 1, 1, 21, 15, 0, 0, tzinfo=timezone.utc),
        )

        self.assertFalse(is_new_event(event, now))
