import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from django.db.models import Count
from django.utils import timezone
from ninja import Router
from pydantic import BaseModel

from app.errors import ErrorResponse
from authentication import AuthBearer, AuthOptional
from eveonline.models import EvePrimaryCharacter
from discord.client import DiscordClient
from fittings.models import EveDoctrine

from .models import (
    EveFleet,
    EveFleetAudience,
    EveFleetInstance,
    EveFleetInstanceMember,
    EveFleetLocation,
    EveStandingFleet,
)
from .notifications import get_fleet_discord_notification


router = Router(tags=["Fleets"])
logger = logging.getLogger(__name__)


class EveFleetType(str, Enum):
    STRATEGIC = "strategic"
    NON_STRATEGIC = "non_strategic"
    TRAINING = "training"


class EveFleetChannelResponse(BaseModel):
    id: int
    display_name: str
    display_channel_name: str


class EveFleetTrackingResponse(BaseModel):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    is_registered: bool

    class Config:
        from_attributes = True


class EveFleetListResponse(BaseModel):
    id: int
    audience: str


class EveFleetResponse(BaseModel):
    """
    Response model for fleet objects
    """

    id: int
    type: EveFleetType
    audience: str
    description: str
    start_time: Optional[datetime] = None
    fleet_commander: int
    doctrine_id: Optional[int] = None
    location: str
    disable_motd: bool = False
    status: Optional[str] = None

    tracking: Optional[EveFleetTrackingResponse] = None


class EveStandingFleetResponse(BaseModel):
    id: int
    character_id: int
    character_name: str
    start_time: datetime
    end_time: Optional[datetime] = None


class EveFleetMemberResponse(BaseModel):
    character_id: int
    character_name: str
    ship_type_id: int
    ship_type_name: str
    solar_system_id: int
    solar_system_name: str


class EveFleetLocationResponse(BaseModel):
    location_id: int
    location_name: str
    solar_system_id: int
    solar_system_name: str


class EveFleetUsersResponse(BaseModel):
    fleet_id: int
    user_ids: List[int]


class CreateEveFleetRequest(BaseModel):
    type: EveFleetType
    description: str
    start_time: datetime
    doctrine_id: Optional[int] = None
    audience_id: int
    location_id: int
    disable_motd: bool = False
    immediate_ping: bool = False


class UpdateEveFleetRequest(BaseModel):
    type: EveFleetType
    description: str
    start_time: datetime
    doctrine_id: Optional[int] = None
    audience_id: int
    location_id: int
    disable_motd: bool = False


class CreateEveFleetReimbursementRequest(BaseModel):
    external_killmail_link: str


class EveFleetReimbursementResponse(BaseModel):
    id: int
    fleet_id: int
    external_killmail_link: str
    status: str
    character_id: int
    primary_character_id: int
    killmail_id: int
    amount: int


@router.get(
    "/types",
    auth=AuthBearer(),
    response={200: List[EveFleetType], 403: ErrorResponse},
)
def get_fleet_types(request):
    if not request.user.has_perm("fleets.add_evefleet"):
        return 403, {"detail": "User missing permission fleets.add_evefleet"}
    return [
        EveFleetType.STRATOP,
        EveFleetType.NON_STRATEGIC,
        EveFleetType.CASUAL,
        EveFleetType.TRAINING,
    ]


@router.get(
    "/v2/locations",
    auth=AuthBearer(),
    response={200: List[EveFleetLocationResponse], 403: ErrorResponse},
)
def get_v2_fleet_locations(request):
    if not request.user.has_perm("fleets.add_evefleet"):
        return 403, {"detail": "User missing permission fleets.add_evefleet"}
    response = []
    locations = (
        EveFleetLocation.objects.all()
        .annotate(count=Count("evefleet__id"))
        .order_by("-count")
    )
    for location in locations:
        response.append(
            {
                "location_id": location.location_id,
                "location_name": location.location_name,
                "solar_system_id": location.solar_system_id,
                "solar_system_name": location.solar_system_name,
            }
        )
    return response


@router.get(
    "/audiences",
    auth=AuthBearer(),
    response={200: List[EveFleetChannelResponse], 403: ErrorResponse},
)
def get_fleet_audiences(request):
    if not request.user.has_perm("fleets.add_evefleet"):
        return 403, {"detail": "User missing permission fleets.add_evefleet"}
    audiences = EveFleetAudience.objects.all()
    response = []
    for audience in audiences:
        response.append(
            {
                "id": audience.id,
                "display_name": audience.name,
                "display_channel_name": audience.discord_channel_name,
            }
        )
    return response


@router.get("", response={200: List[int]})
def get_fleets(request, upcoming: bool = True, active: bool = False):
    if active:
        fleets = (
            EveFleet.objects.filter(evefleetinstance__end_time=None)
            .filter(start_time__gte=timezone.now() - timedelta(hours=1))
            .order_by("-start_time")
        )
    elif upcoming:
        fleets = EveFleet.objects.filter(
            start_time__gte=timezone.now()
        ).order_by("-start_time")
    else:
        # get fleets from past 30 days
        fleets = EveFleet.objects.filter(
            start_time__gte=timezone.now() - timedelta(days=30)
        ).order_by("-start_time")
    return [fleet.id for fleet in fleets]


@router.get("/v2", response={200: List[EveFleetListResponse]})
def get_v2_fleets(request, upcoming: bool = True, active: bool = False):
    if active:
        fleets = (
            EveFleet.objects.filter(evefleetinstance__end_time=None)
            .filter(start_time__gte=timezone.now() - timedelta(hours=1))
            .order_by("-start_time")
        )
    elif upcoming:
        fleets = EveFleet.objects.filter(
            start_time__gte=timezone.now()
        ).order_by("-start_time")
    else:
        # get fleets from past 30 days
        fleets = EveFleet.objects.filter(
            start_time__gte=timezone.now() - timedelta(days=30)
        ).order_by("-start_time")
    response = []
    for fleet in fleets:
        response.append(
            {
                "id": fleet.id,
                "audience": fleet.audience.name,
            }
        )
    return response


class EveFleetFilter(str, Enum):
    ACTIVE = "active"
    UPCOMING = "upcoming"
    RECENT = "recent"


@router.get(
    "/v3",
    response={
        200: List[EveFleetResponse],
        401: ErrorResponse,
        403: ErrorResponse,
    },
    auth=AuthOptional(),
    description="Get full details of fleets matching the specified filter.",
)
def get_v3_fleets(
    request, fleet_filter: EveFleetFilter = EveFleetFilter.RECENT
) -> List[EveFleetResponse]:
    if fleet_filter == EveFleetFilter.ACTIVE:
        fleets = (
            EveFleet.objects.filter(evefleetinstance__end_time=None)
            .filter(start_time__gte=timezone.now() - timedelta(hours=1))
            .order_by("-start_time")
        )
    elif fleet_filter == EveFleetFilter.UPCOMING:
        fleets = EveFleet.objects.filter(
            start_time__gte=timezone.now()
        ).order_by("-start_time")
    else:
        # get fleets from past 30 days
        fleets = EveFleet.objects.filter(
            start_time__gte=timezone.now() - timedelta(days=30)
        ).order_by("-start_time")
    response = []
    for fleet in fleets:
        if can_see_fleet(fleet, request.user):
            response.append(make_fleet_response(fleet))
        else:
            response.append(make_fleet_shadow(fleet))
    return response


def can_see_fleet(fleet: EveFleet, user) -> bool:
    if not user.id:
        return False
    if user.has_perm("fleets.view_evefleet"):
        return True
    if user == fleet.created_by:
        return True
    for group in fleet.audience.groups.all():
        if group in user.groups.all():
            return True
    return False


def make_fleet_response(fleet: EveFleet) -> EveFleetResponse:
    tracking = None
    if EveFleetInstance.objects.filter(eve_fleet=fleet).exists():
        tracking = EveFleetTrackingResponse.model_validate(
            EveFleetInstance.objects.get(eve_fleet=fleet)
        )

    return {
        "id": fleet.id,
        "type": fleet.type,
        "description": fleet.description,
        "start_time": fleet.start_time,
        "fleet_commander": fleet.created_by.id if fleet.created_by else 0,
        "location": (
            fleet.location.location_name if fleet.location else "Ask FC"
        ),
        "audience": fleet.audience.name,
        "tracking": tracking,
        "disable_motd": fleet.disable_motd,
        "status": fleet.status,
    }


def make_fleet_shadow(fleet: EveFleet) -> EveFleetResponse:
    """Makes a shadow response with no fleet details"""
    return {
        "id": fleet.id,
        "type": "non_strategic",
        "description": "Unavailable",
        "start_time": None,
        "fleet_commander": 0,
        "location": "Unavailable",
        "audience": fleet.audience.name,
        "tracking": None,
        "disable_motd": False,
        "status": None,
    }


@router.get("/standingfleets", response={200: List[EveStandingFleetResponse]})
def get_standing_fleets(request, active: bool = True):
    standing_fleets = EveStandingFleet.objects.filter(end_time=None)
    if active:
        standing_fleets = standing_fleets.filter(end_time=None)
    response = []
    for standing_fleet in standing_fleets:
        response.append(
            {
                "id": standing_fleet.id,
                "character_id": standing_fleet.active_fleet_commander_character_id,
                "character_name": standing_fleet.active_fleet_commander_character_name,
                "start_time": standing_fleet.start_time,
                "end_time": standing_fleet.end_time,
            }
        )
    return response


@router.post(
    "/standing",
    auth=AuthBearer(),
    response={200: None, 403: ErrorResponse, 400: ErrorResponse},
    description="Create a standing fleet, must have fleets.add_evestandingfleet permission",
)
def create_standing_fleet(request):
    if not request.user.has_perm("fleets.add_evestandingfleet"):
        return 403, {
            "detail": "User missing permission fleets.add_evestandingfleet"
        }

    eve_primary_character = EvePrimaryCharacter.objects.get(
        character__token__user=request.user
    )
    try:
        EveStandingFleet.start(eve_primary_character.character.character_id)
    except Exception as e:
        return 400, {
            "detail": f"Error starting fleet for {eve_primary_character.character}: {e}"
        }

    return 200, None


@router.post(
    "/standing/{fleet_id}/claim",
    auth=AuthBearer(),
    response={200: None, 403: ErrorResponse, 400: ErrorResponse},
    description="End a standing fleet, must have fleets.end_evestandingfleet permission",
)
def claim_standing_fleet(request, fleet_id: int):
    if not request.user.has_perm("fleets.end_evestandingfleet"):
        return 403, {
            "detail": "User missing permission fleets.end_evestandingfleet"
        }

    standing_fleet = EveStandingFleet.objects.get(id=fleet_id)
    eve_primary_character = EvePrimaryCharacter.objects.get(
        character__token__user=request.user
    )

    standing_fleet.claim(eve_primary_character.character.character_id)

    return 200, None


@router.get(
    "/{fleet_id}",
    auth=AuthBearer(),
    response={200: EveFleetResponse, 403: None, 404: None},
    description="Get fleet by ID, must be the owner, in the audience, or have fleets.view_evefleet permission",
)
def get_fleet(request, fleet_id: int):
    fleet = EveFleet.objects.filter(id=fleet_id).first()
    if not fleet:
        return 404, None
    is_authorized = False
    if request.user.has_perm("fleets.view_evefleet"):
        is_authorized = True
    if request.user == fleet.created_by:
        is_authorized = True
    for group in fleet.audience.groups.all():
        if group in request.user.groups.all():
            is_authorized = True

    if not is_authorized:
        return 403, None

    tracking = None
    if EveFleetInstance.objects.filter(eve_fleet=fleet).exists():
        tracking = EveFleetTrackingResponse.model_validate(
            EveFleetInstance.objects.get(eve_fleet=fleet)
        )

    payload = {
        "id": fleet.id,
        "type": fleet.type,
        "description": fleet.description,
        "start_time": fleet.start_time,
        "fleet_commander": fleet.created_by.id if fleet.created_by else 0,
        "location": (
            fleet.location.location_name if fleet.location else "Ask FC"
        ),
        "audience": fleet.audience.name,
        "tracking": tracking,
        "disable_motd": fleet.disable_motd,
        "status": fleet.status,
    }
    if fleet.doctrine:
        payload["doctrine_id"] = fleet.doctrine.id

    return EveFleetResponse(**payload)


@router.get(
    "/{fleet_id}/users",
    response={200: List[EveFleetUsersResponse], 403: None, 404: None},
    description="Get users for a given fleet, no permissions required",
)
def get_fleet_users(request, fleet_id: int):
    fleet = EveFleet.objects.filter(id=fleet_id).first()
    if not fleet:
        return 404, None

    audience = fleet.audience
    groups = audience.groups.all()

    # get all users with a group in the audience
    users = set()
    for group in groups:
        for user in group.user_set.all():
            users.add(user.id)

    return [{"fleet_id": fleet_id, "user_ids": list(users)}]


@router.get(
    "/{fleet_id}/members",
    auth=AuthBearer(),
    response={200: List[EveFleetMemberResponse], 403: None, 404: None},
    description="Get fleet members, must be the owner, in the audience, or have fleets.view_evefleet permission",
)
def get_fleet_members(request, fleet_id: int):
    fleet = EveFleet.objects.filter(id=fleet_id).first()
    if not fleet:
        return 404, None
    is_authorized = False
    if request.user.has_perm("fleets.view_evefleet"):
        is_authorized = True
    if request.user == fleet.created_by:
        is_authorized = True
    if fleet.audience in request.user.groups.all():
        is_authorized = True

    if not is_authorized:
        return 403, None

    response = []
    for member in EveFleetInstanceMember.objects.filter(
        eve_fleet_instance__eve_fleet=fleet
    ):
        response.append(
            {
                "character_id": member.character_id,
                "character_name": member.character_name,
                "ship_type_id": member.ship_type_id,
                "ship_type_name": member.ship_name,
                "solar_system_id": member.solar_system_id,
                "solar_system_name": member.solar_system_name,
            }
        )

    return response


@router.post(
    "",
    auth=AuthBearer(),
    response={200: EveFleetResponse, 403: ErrorResponse, 400: ErrorResponse},
    description="Create a new fleet, type/location/audience is from other endpoints. Must have fleets.add_evefleet permission",
)
def create_fleet(request, payload: CreateEveFleetRequest):
    if not request.user.has_perm("fleets.add_evefleet"):
        return 403, {"detail": "User missing permission fleets.add_evefleet"}

    if not EveFleetAudience.objects.filter(id=payload.audience_id).exists():
        return 400, {"detail": "Audience does not exist"}

    if not EveFleetLocation.objects.filter(
        location_id=payload.location_id
    ).exists():
        return 400, {"detail": "Location does not exist"}

    audience = EveFleetAudience.objects.get(id=payload.audience_id)
    fleet = EveFleet.objects.create(
        type=payload.type,
        description=payload.description,
        start_time=payload.start_time,
        created_by=request.user,
        location=EveFleetLocation.objects.get(location_id=payload.location_id),
        audience=audience,
        disable_motd=payload.disable_motd,
        status="pending",
    )

    if payload.doctrine_id:
        doctrine = EveDoctrine.objects.get(id=payload.doctrine_id)
        fleet.doctrine = doctrine
        fleet.save()

    if not fleet.audience.add_to_schedule:
        # Remove this once the fleet creation UI is sending it
        payload.immediate_ping = True

    if payload.immediate_ping:
        send_discord_pre_ping(fleet)

    payload = {
        "id": fleet.id,
        "type": fleet.type,
        "description": fleet.description,
        "start_time": fleet.start_time,
        "fleet_commander": fleet.created_by.id,
        "location": fleet.location.location_name,
        "audience": fleet.audience.name,
    }

    if fleet.doctrine:
        payload["doctrine_id"] = fleet.doctrine.id

    return EveFleetResponse(**payload)


def send_discord_pre_ping(fleet: EveFleet) -> bool:
    """Send a Discord pre-ping for a fleet"""
    notification = get_fleet_discord_notification(
        is_pre_ping=True,
        fleet_id=fleet.id,
        fleet_type=fleet.get_type_display(),
        fleet_location=fleet.location.location_name,
        fleet_audience=fleet.audience.name,
        fleet_commander_name=fleet.fleet_commander.character_name,
        fleet_commander_id=fleet.fleet_commander.character_id,
        fleet_description=fleet.description,
        fleet_voice_channel=fleet.audience.discord_voice_channel_name,
        fleet_voice_channel_link=fleet.audience.discord_voice_channel,
        fleet_start_time=fleet.start_time,
    )

    try:
        DiscordClient().create_message(
            channel_id=fleet.audience.discord_channel_id,
            payload=notification,
        )
        return True
    except Exception as e:
        logger.error(
            "Error sending Discord pre-ping for fleet %d : %s",
            fleet.id,
            str(e),
        )
        return False


@router.patch(
    "/{fleet_id}",
    auth=AuthBearer(),
    response={200: EveFleetResponse, 403: ErrorResponse, 400: ErrorResponse},
    description="Update the fleet details. Must have fleets.add_evefleet permission",
)
def update_fleet(request, fleet_id: int, payload: UpdateEveFleetRequest):
    if not request.user.has_perm("fleets.add_evefleet"):
        return 403, {"detail": "User missing permission fleets.add_evefleet"}

    fleet = EveFleet.objects.get(id=fleet_id)

    if not EveFleetAudience.objects.filter(id=payload.audience_id).exists():
        return 400, {"detail": "Audience does not exist"}

    if not EveFleetLocation.objects.filter(
        location_id=payload.location_id
    ).exists():
        return 400, {"detail": "Location does not exist"}

    audience = EveFleetAudience.objects.get(id=payload.audience_id)
    fleet.type = payload.type
    fleet.description = payload.description
    fleet.start_time = payload.start_time
    fleet.location = EveFleetLocation.objects.get(
        location_id=payload.location_id
    )
    fleet.audience = audience

    if payload.doctrine_id:
        doctrine = EveDoctrine.objects.get(id=payload.doctrine_id)
        fleet.doctrine = doctrine

    fleet.save()

    payload = {
        "id": fleet.id,
        "type": fleet.type,
        "description": fleet.description,
        "start_time": fleet.start_time,
        "fleet_commander": fleet.created_by.id,
        "location": fleet.location.location_name,
        "audience": fleet.audience.name,
    }

    if fleet.doctrine:
        payload["doctrine_id"] = fleet.doctrine.id

    return EveFleetResponse(**payload)


@router.post(
    "/{fleet_id}/tracking",
    auth=AuthBearer(),
    response={200: None, 403: ErrorResponse, 400: ErrorResponse},
    description="Start a fleet and send a discord ping, must be the owner of the fleet",
)
def start_fleet(request, fleet_id: int):
    fleet = EveFleet.objects.get(id=fleet_id)
    if request.user != fleet.created_by:
        return 403, {
            "detail": "User does not have permission to start tracking this fleet"
        }
    try:
        fleet.start()
    except Exception as e:
        return 400, {"detail": str(e)}

    return 200, None


@router.delete(
    "/{fleet_id}",
    auth=AuthBearer(),
    response={200: None, 403: ErrorResponse},
    description="Delete a fleet, must be owner or have fleets.delete_evefleet permission",
)
def delete_fleet(request, fleet_id: int):
    fleet = EveFleet.objects.get(id=fleet_id)
    if request.user != fleet.created_by and not request.user.has_perm(
        "fleets.delete_evefleet"
    ):
        return 403, {
            "detail": "User does not have permission to delete this fleet"
        }
    fleet.delete()
    return 200, None


@router.post(
    "/{fleet_id}/preping",
    auth=AuthBearer(),
    response={202: None, 403: ErrorResponse, 404: ErrorResponse, 500: None},
    description="Send a Discord pre-ping for a fleet. No request body needed.",
)
def send_pre_ping(request, fleet_id):
    fleet = EveFleet.objects.filter(id=fleet_id).first()

    if not fleet:
        return 404, ErrorResponse(detail="Fleet not found")

    if request.user != fleet.created_by:
        return 403, {
            "detail": "User does not have permission to delete this fleet"
        }

    sent = send_discord_pre_ping(fleet)

    if sent:
        return 202
    else:
        return 500
