from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.engine import Engine

from app.admin.auth import admin_authentication_backend
from app.admin.views import UserAdmin


def setup_admin(app: FastAPI, engine: Engine) -> Admin:
    """
    Mounts and configures SQLAdmin on the FastAPI application instance.
    Minimal panel: only user/access management is exposed here. All content
    (services, case studies, talent, social proof, careers, leads) is
    controlled from the frontend admin portal via the public API.
    """
    admin = Admin(
        app=app,
        engine=engine,
        title="Agency CMS - Access",
        logo_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&auto=format&fit=crop&q=80",
        authentication_backend=admin_authentication_backend,
        base_url="/admin",
    )

    # Only access management lives in the backend admin UI
    admin.add_view(UserAdmin)

    return admin
