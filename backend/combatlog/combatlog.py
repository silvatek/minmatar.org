from typing import Dict, List


class LogEvent:
    raw_log: str
    event_time: str
    event_type: str
    text: str


class DamageEvent:
    event_time: str
    damage: int = 0
    direction: str
    entity: str
    weapon: str
    outcome: str
    text: str


class LogAnalysis:
    logged_events: int
    damage_done: int
    damage_taken: int


def parse_line(line: str) -> LogEvent:
    line = line.strip()

    if line.startswith("["):
        pos = line.find("]")

        event = LogEvent()

        event.event_time = line[1 : pos - 1].strip()
        text = line[pos + 1 :].strip()

        pos = text.find(")")
        if pos == -1:
            event.event_type = "unknown"
        else:
            event.event_type = text[1:pos].strip()
            text = text[pos + 1 :]

        event.text = strip_html(text)
    else:
        event = LogEvent()
        event.event_time = ""
        event.event_type = "unknown"
        event.text = line

    return event


def parse(text: str) -> List[LogEvent]:
    events = []
    for line in text.splitlines():
        event = parse_line(line)
        events.append(event)

    return events


def strip_html(text):
    text = text.strip()
    start = text.find("<")
    while start >= 0:
        end = text.find(">")
        if start > 0:
            text = text[0:start] + text[end + 1 :]
        else:
            text = text[end + 1 :]
        start = text.find("<")

    return text


def damage_events(events: List[LogEvent]) -> List[DamageEvent]:
    dmg_events = []
    for event in events:
        if event.event_type != "combat":
            continue

        text = event.text

        if len(text) == 0:
            continue

        if text[0] < "0" or text[0] > "9":
            continue

        damage_event = DamageEvent()
        damage_event.event_time = event.event_time

        pos = text.find(" to ")
        if pos >= 0:
            damage_event.damage = int(text[0:pos])
            damage_event.direction = "to"
            text = text[pos + 4 :]

        pos = text.find(" from ")
        if pos >= 0:
            damage_event.damage = int(text[0:pos])
            damage_event.direction = "from"
            text = text[pos + 6 :]

        parts = text.split("-")
        if len(parts) >= 1:
            damage_event.entity = parts[0].strip()
        if len(parts) >= 3:
            damage_event.weapon = parts[1].strip()
            damage_event.outcome = parts[2].strip()
        elif len(parts) == 2:
            damage_event.weapon = ""
            damage_event.outcome = parts[1].strip()

        if damage_event.damage > 0:
            damage_event.text = text
            dmg_events.append(damage_event)

    return dmg_events


def total_damage(dmg_events):
    total_done = 0
    total_taken = 0
    for event in dmg_events:
        if event.direction == "to":
            total_done += event.damage

        if event.direction == "from":
            total_taken += event.damage

    return (total_done, total_taken)


def enemy_damage(
    dmg_events: List[DamageEvent], direction: str
) -> Dict[str, int]:
    result = {}

    for event in dmg_events:
        if event.direction == direction:
            if event.entity not in result:
                result[event.entity] = 0
            result[event.entity] += event.damage

    return result


def weapon_damage(dmg_events: List[DamageEvent]) -> Dict[str, int]:
    result = {}

    for event in dmg_events:
        if event.direction == "to":
            if event.weapon not in result:
                result[event.weapon] = 0
            result[event.weapon] += event.damage

    return result


def damage_over_time(
    dmg_events: List[DamageEvent], direction: str
) -> Dict[str, int]:
    results: Dict[str, int] = {}

    for event in dmg_events:
        time_bucket = event.event_time[0:-1] + "0"

        if time_bucket not in results:
            results[time_bucket] = 0

        if event.direction == direction:
            results[time_bucket] += event.damage

    return results
