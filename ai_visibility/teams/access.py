from __future__ import annotations

from django.core.exceptions import PermissionDenied

from ai_visibility.teams.models import Membership
from ai_visibility.teams.models import Team


def teams_for(user):
    """Teams the user belongs to."""
    return Team.objects.filter(memberships__user=user)


def require_team_member(user, team: Team) -> Membership:
    """Return the user's membership on the team, or raise PermissionDenied."""
    membership = Membership.objects.filter(user=user, team=team).first()
    if membership is None:
        msg = "Not a member of this team"
        raise PermissionDenied(msg)
    return membership


def require_role(user, team: Team, *roles: str) -> Membership:
    """Return the membership if its role is one of ``roles``, else raise."""
    membership = require_team_member(user, team)
    if membership.role not in roles:
        msg = "Insufficient role"
        raise PermissionDenied(msg)
    return membership
