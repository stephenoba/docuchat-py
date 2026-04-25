from typing import Annotated, List
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_events.dispatcher import dispatch
from sqlmodel import select, and_, desc, asc, func

from auth import PermissionChecker
from models import User, Document
from schemas import SuccessResponse
from schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from dbmanager import async_session
from config import DOCUMENT_EVENTS

document_router = APIRouter()


@document_router.post(
    "",
    response_model=SuccessResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    user: Annotated[User, Depends(PermissionChecker("documents:create"))],
    data: DocumentCreate,
):
    document = await Document.objects.create(
        user_id=user.id,
        title=data.title,
        content=data.content,
        filename=data.filename or data.title,
        file_size_bytes=len(data.content.encode("utf-8")),
        status="completed",
    )

    # Log and Dispatch
    metadata = {
        "title": document.title,
        "filename": document.filename,
        "file_size": document.file_size_bytes,
        "timestamp": datetime.now().isoformat(),
    }
    dispatch(DOCUMENT_EVENTS.CREATED, payload={"user_id": user.id, **metadata})

    # Simulate processing (for now)
    processing_start = datetime.now()
    # Mocking chunking
    num_chunks = max(1, len(data.content) // 500)
    document.chunk_count = num_chunks
    await Document.objects.save(document)
    processing_end = datetime.now()
    duration_ms = int((processing_end - processing_start).total_seconds() * 1000)

    # Log and Dispatch Processed
    processed_metadata = {
        "document_id": str(document.id),
        "chunk_count": num_chunks,
        "duration_ms": duration_ms,
    }
    dispatch(DOCUMENT_EVENTS.PROCESSED, payload={"user_id": user.id, **processed_metadata})

    return SuccessResponse[DocumentResponse](
        data=DocumentResponse.model_validate(document),
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

    from schemas import PaginationMeta

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
        document.updated_at = datetime.now()
        await Document.objects.save(document)

    return SuccessResponse[DocumentResponse](
        data=DocumentResponse.model_validate(document),
        message="Document updated successfully",
    )


@document_router.delete("/{document_id}", response_model=SuccessResponse)
async def delete_document(
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
    document.deleted_at = datetime.now()
    document.deleted_by = user.id
    await Document.objects.save(document)

    # Log and Dispatch
    metadata = {
        "document_id": str(document_id),
        "title": document.title,
        "deleted_at": document.deleted_at.isoformat(),
        "deleted_by": str(user.id),
    }
    dispatch(DOCUMENT_EVENTS.DELETED, payload={"user_id": user.id, **metadata})

    return SuccessResponse(message="Document deleted successfully")


@document_router.post(
    "/{document_id}/restore", response_model=SuccessResponse[DocumentResponse]
)
async def restore_document(
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
        "restored_at": datetime.now().isoformat(),
    }
    dispatch(DOCUMENT_EVENTS.RESTORED, payload={"user_id": user.id, **metadata})

    return SuccessResponse[DocumentResponse](
        data=DocumentResponse.model_validate(document),
        message="Document restored successfully",
    )
