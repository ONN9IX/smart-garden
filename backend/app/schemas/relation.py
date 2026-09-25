"""Relation input; the server resolves both IDs inside the authenticated tenant."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RelationType = Literal["mother", "father", "legal_guardian", "other"]


class RelationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guardian_id: UUID
    relation_type: RelationType


class RelationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relation_type: RelationType
