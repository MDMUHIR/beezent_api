from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    CLIENT = "client"
    STAFF = "staff"
    ADMIN = "admin"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class TeamMemberCategory(StrEnum):
    LEADERSHIP = "leadership"
    TALENT = "talent"


class DemoVideoType(StrEnum):
    YOUTUBE = "youtube"
    UPLOAD = "upload"
