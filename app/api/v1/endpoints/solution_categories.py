from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Solution, SolutionCategory
from app.schemas import SolutionCategoryDetail, SolutionCategoryPublic

router = APIRouter(prefix="/solution-categories", tags=["solution-categories"])


@router.get("", response_model=list[SolutionCategoryPublic])
async def list_solution_categories(
    session: AsyncSession = Depends(get_session),
) -> list[SolutionCategory]:
    stmt = select(SolutionCategory).order_by(
        SolutionCategory.sort_order.asc(),
        SolutionCategory.name.asc(),
    )
    return list((await session.scalars(stmt)).all())


@router.get("/{slug}", response_model=SolutionCategoryDetail)
async def get_solution_category(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> SolutionCategoryDetail:
    """Return a category together with its published solutions."""
    category = await session.scalar(
        select(SolutionCategory).where(SolutionCategory.slug == slug)
    )
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    solutions_stmt = (
        select(Solution)
        .join(Solution.categories)
        .where(SolutionCategory.slug == slug, Solution.published.is_(True))
        .order_by(Solution.sort_order.asc(), Solution.name.asc())
    )
    solutions = list((await session.scalars(solutions_stmt)).all())

    return SolutionCategoryDetail(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        sort_order=category.sort_order,
        solutions=solutions,
    )
