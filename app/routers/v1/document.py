from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, File, UploadFile, Form
from fastapi_events.dispatcher import dispatch
from sqlmodel import select, and_, desc, asc, func
from celery.result import AsyncResult

from app.auth import PermissionChecker
from app.models.models import User, Document, DocumentStatus
from app.schemas import SuccessResponse
from app.schemas.document import DocumentUpdate, DocumentResponse, DocumentStatusUpdate
from app.models.dbmanager import async_session
from app.queues.celery_task import process_document
from app.core.config import DOCUMENT_EVENTS
from app.core.utils import utcnow
from app.dependencies.rate_limiter import general_limiter, upload_limiter


document_router = APIRouter(dependencies=[Depends(general_limiter)])

@document_router.post(
    "",
    response_model=SuccessResponse[DocumentResponse],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(upload_limiter)],
)
async def create_document(
    request: Request,
    user: Annotated[User, Depends(PermissionChecker("documents:create"))],
    file: UploadFile = File(...),
    title: str = Form(...),
):
    # Read file content
    content = await file.read()
    filename = file.filename or title
    
    document = await Document.objects.create(
        user_id=user.id,
        title=title,
        content=content,
        filename=filename,
        mime_type=file.content_type,
        file_size_bytes=len(content),
    )

    # Log and Dispatch
    metadata = {
        "title": document.title,
        "filename": document.filename,
        "file_size": document.file_size_bytes,
        "timestamp": utcnow().isoformat(),
        "correlation_id": str(request.state.correlation_id)
    }
    dispatch(DOCUMENT_EVENTS.CREATED, payload={"user_id": user.id, **metadata})

    task = process_document.delay(
        document_id=str(document.id),
        user_id=str(user.id),
        correlation_id=str(request.state.correlation_id)
    )

    response_data = DocumentResponse.model_validate(document)
    response_data.task_id = task.id

    return SuccessResponse[DocumentResponse](
        data=response_data,
        message="Document created successfully",
    )

@document_router.get("", response_model=SuccessResponse[List[DocumentResponse]])
async def list_documents(
    user: Annotated[User, Depends(PermissionChecker("documents:read"))],
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by title"),
    sort: str | None = Query("-created_at", description="Sort by fields (e.g. title,-created_at)"),
    skip: int = 0,
    limit: int = 100,
):
    async with async_session() as session:
        # Base filter and search logic
        base_query = select(Document).where(
            and_(
                Document.user_id == user.id,
                Document.deleted_at == None,  # noqa: E711
            )
        )

        if status:
            base_query = base_query.where(Document.status == status)

        if search:
            base_query = base_query.where(Document.title.ilike(f"%{search}%"))

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting
        statement = base_query
        if sort:
            sort_fields = sort.split(",")
            for field in sort_fields:
                field = field.strip()
                if field.startswith("-"):
                    column_name = field[1:]
                    column = getattr(Document, column_name, None)
                    if column:
                        statement = statement.order_by(desc(column))
                else:
                    column_name = field
                    column = getattr(Document, column_name, None)
                    if column:
                        statement = statement.order_by(asc(column))

        statement = statement.offset(skip).limit(limit)
        results = await session.execute(statement)
        documents = results.scalars().all()

    from app.schemas import PaginationMeta

    return SuccessResponse[List[DocumentResponse]](
        data=[DocumentResponse.model_validate(d) for d in documents],
        message="Documents retrieved successfully",
        meta=PaginationMeta(
            page=(skip // limit) + 1 if limit > 0 else 1,
            limit=limit,
            total=total,
        ),
    )


@document_router.get("/{document_id}", response_model=SuccessResponse[DocumentResponse])
async def get_document(
    user: Annotated[User, Depends(PermissionChecker("documents:read"))],
    document_id: UUID,
):
    document = await Document.objects.get(
        id=document_id, user_id=user.id, deleted_at=None
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return SuccessResponse[DocumentResponse](
        data=DocumentResponse.model_validate(document),
        message="Document retrieved successfully",
    )

@document_router.get("/{document_id}/processing-status", response_model=SuccessResponse[DocumentStatusUpdate])
async def get_document_processing_status(
    user: Annotated[User, Depends(PermissionChecker("documents:read"))],
    document_id: UUID,
):
    document = await Document.objects.get(
        id=document_id, user_id=user.id, deleted_at=None
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    task_id = document.task_id
    if task_id:
        from app.queues.celery_task import app as celery_app
        task = AsyncResult(task_id, app=celery_app)
        if task.state == "PENDING" and document.status != DocumentStatus.PENDING.value:
            document.status = DocumentStatus.PENDING.value
        elif task.state == "PROGRESS" and document.status != DocumentStatus.PROCESSING.value:
            document.status = DocumentStatus.PROCESSING.value
        elif task.state == "SUCCESS" and document.status != DocumentStatus.READY.value:
            document.status = DocumentStatus.READY.value
        elif task.state == "FAILURE" and document.status != DocumentStatus.FAILED.value:
            document.status = DocumentStatus.FAILED.value
            document.error = str(task.info)

        await Document.objects.save(document)

    return SuccessResponse[DocumentStatusUpdate](
        data=DocumentStatusUpdate.model_validate(document),
        message="Document processing status retrieved successfully",
    )


@document_router.patch(
    "/{document_id}", response_model=SuccessResponse[DocumentResponse]
)
async def update_document(
    user: Annotated[User, Depends(PermissionChecker("documents:update"))],
    document_id: UUID,
    data: DocumentUpdate,
):
    document = await Document.objects.get(
        id=document_id, user_id=user.id, deleted_at=None
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(document, key, value)
        document.updated_at = utcnow()
        await Document.objects.save(document)

    return SuccessResponse[DocumentResponse](
        data=DocumentResponse.model_validate(document),
        message="Document updated successfully",
    )


@document_router.delete("/{document_id}", response_model=SuccessResponse)
async def delete_document(
    request: Request,
    user: Annotated[User, Depends(PermissionChecker("documents:delete"))],
    document_id: UUID,
):
    document = await Document.objects.get(
        id=document_id, user_id=user.id, deleted_at=None
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Soft delete
    document.deleted_at = utcnow()
    document.deleted_by = user.id
    await Document.objects.save(document)

    # Log and Dispatch
    metadata = {
        "document_id": str(document_id),
        "title": document.title,
        "deleted_at": document.deleted_at.isoformat(),
        "deleted_by": str(user.id),
        "correlation_id": str(request.state.correlation_id)
    }
    dispatch(DOCUMENT_EVENTS.DELETED, payload={"user_id": user.id, **metadata})

    return SuccessResponse(message="Document deleted successfully")


@document_router.post(
    "/{document_id}/restore", response_model=SuccessResponse[DocumentResponse]
)
async def restore_document(
    request: Request,
    user: Annotated[User, Depends(PermissionChecker("documents:update"))],
    document_id: UUID,
):
    # Find soft-deleted document or any document of the user
    document = await Document.objects.get(id=document_id, user_id=user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if document.deleted_at is None:
        return SuccessResponse[DocumentResponse](
            data=DocumentResponse.model_validate(document),
            message="Document is already active",
        )

    document.deleted_at = None
    document.deleted_by = None
    await Document.objects.save(document)

    # Log and Dispatch
    metadata = {
        "document_id": str(document_id),
        "title": document.title,
        "restored_at": utcnow().isoformat(),
        "correlation_id": str(request.state.correlation_id)
    }
    dispatch(DOCUMENT_EVENTS.RESTORED, payload={"user_id": user.id, **metadata})

    return SuccessResponse[DocumentResponse](
        data=DocumentResponse.model_validate(document),
        message="Document restored successfully",
    )
