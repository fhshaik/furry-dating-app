from typing import TypeAlias

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.fursona import Fursona
from app.models.message import Message
from app.models.pack import Pack
from app.models.report import Report
from app.models.user import User
from app.schemas.report import (
    ContentReportCreateRequest,
    ReportContentType,
    ReportResponse,
    UserReportCreateRequest,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])

ReportTargetModel: TypeAlias = type[Fursona] | type[Message] | type[Pack]

CONTENT_REPORT_MODELS: dict[ReportContentType, ReportTargetModel] = {
    "fursona": Fursona,
    "message": Message,
    "pack": Pack,
}


@router.post("/users", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_user_report(
    payload: UserReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Report:
    if payload.reported_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot report yourself",
        )

    reported_user = await db.get(User, payload.reported_user_id)
    if reported_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reported user not found",
        )

    report = Report(
        reporter_id=current_user.id,
        reported_user_id=reported_user.id,
        reason=payload.reason,
        details=payload.details,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.post("/content", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_content_report(
    payload: ContentReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Report:
    model = CONTENT_REPORT_MODELS[payload.content_type]
    target = await db.get(model, payload.content_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reported content not found",
        )

    report = Report(
        reporter_id=current_user.id,
        content_type=payload.content_type,
        content_id=payload.content_id,
        reason=payload.reason,
        details=payload.details,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
