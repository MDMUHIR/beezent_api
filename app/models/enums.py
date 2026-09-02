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
