from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_case_studies,
    admin_files,
    admin_leads,
    admin_project_categories,
    admin_projects,
    admin_service_categories,
    admin_services,
    admin_solution_categories,
    admin_solutions,
    admin_team_members,
    auth,
    case_studies,
    dev,
    health,
    leads,
    project_categories,
    projects,
    service_categories,
    services,
    solution_categories,
    solutions,
    team_members,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(dev.router)
api_router.include_router(projects.router)
api_router.include_router(project_categories.router)
api_router.include_router(case_studies.router)
api_router.include_router(services.router)
api_router.include_router(service_categories.router)
api_router.include_router(solutions.router)
api_router.include_router(solution_categories.router)
api_router.include_router(team_members.router)
api_router.include_router(leads.router)
api_router.include_router(admin_projects.router)
api_router.include_router(admin_project_categories.router)
api_router.include_router(admin_services.router)
api_router.include_router(admin_service_categories.router)
api_router.include_router(admin_solutions.router)
api_router.include_router(admin_solution_categories.router)
api_router.include_router(admin_team_members.router)
api_router.include_router(admin_case_studies.router)
api_router.include_router(admin_leads.router)
api_router.include_router(admin_files.router)
