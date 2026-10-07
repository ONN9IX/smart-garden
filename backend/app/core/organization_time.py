"""Organization-local calendar helpers backed by validated IANA timezones."""

from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_ORGANIZATION_TIMEZONE = "Europe/Moscow"


class OrganizationClock(Protocol):
    timezone: str


def organization_zone(value: str) -> ZoneInfo:
    """Build a ZoneInfo or fail closed for invalid tenant configuration."""
    try:
        return ZoneInfo(value)
    except (TypeError, ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError("timezone must be a valid IANA timezone") from error


def validate_iana_timezone(value: str) -> str:
    """Return the validated canonical IANA key for persistence."""
    return organization_zone(value).key


def organization_today(organization: OrganizationClock) -> date:
    """Return the current calendar date in the authenticated tenant's timezone."""
    return datetime.now(organization_zone(organization.timezone)).date()


def organization_now(organization: OrganizationClock) -> datetime:
    """Return the current timezone-aware datetime in the tenant's timezone."""
    return datetime.now(organization_zone(organization.timezone))
