import logging

from typing import List

from django.contrib.auth.models import User

from eveonline.models import (
    EvePlayer,
    EveCharacter,
    EvePrimaryCharacterChangeLog,
)
from eveonline.scopes import TokenType, scopes_for


logger = logging.getLogger(__name__)


def user_primary_character(user: User) -> EveCharacter | None:
    """Returns the primary character for a particular User"""

    player = user_player(user)
    if player and player.primary_character:
        return player.primary_character
    else:
        return None


def user_characters(user: User) -> List[EveCharacter]:
    """Returns all the EveCharacters for a particular User"""
    return EveCharacter.objects.filter(user=user).all()


def character_primary(character: EveCharacter) -> EveCharacter | None:
    """Returns the primary character for a character"""
    if not character:
        return None
    if character.user:
        return user_primary_character(character.user)
    else:
        return user_primary_character(character.token.user)


def set_primary_character(user: User, character: EveCharacter):
    """Sets the primary character for a user"""

    current_primary = user_primary_character(user)
    if current_primary and (current_primary != character):
        EvePrimaryCharacterChangeLog.objects.create(
            username=user.username,
            previous_character_name=current_primary.character_name,
            new_character_name=character.character_name,
        )
        current_primary.is_primary = False
        current_primary.save()

    character.user = user
    character.is_primary = True
    character.save()

    player = user_player(user)
    if player:
        player.primary_character = character
        player.save()
    else:
        EvePlayer.objects.create(
            user=user, primary_character=character, nickname=user.username
        )


def user_player(user: User) -> EvePlayer | None:
    return EvePlayer.objects.filter(user=user).first()


def player_characters(player: EvePlayer) -> List[EveCharacter]:
    return user_characters(player.user)


def character_desired_scopes(character: EveCharacter) -> List[str]:
    if not character.esi_token_level:
        return []

    token_type = TokenType(character.esi_token_level)
    if not token_type:
        return []

    return scopes_for(token_type)
