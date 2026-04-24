from typing import Annotated, List
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, and_

from auth import PermissionChecker
from models import User, Document
from schemas import SuccessResponse
from schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from dbmanager import async_session

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
        status="completed",  # Assuming it's simple for now, usually would be 'pending' during processing
    )
    return SuccessResponse[DocumentResponse](
        data=DocumentResponse.model_validate(document),
        message="Document created successfully",
    )


@document_router.get("", response_model=SuccessResponse[List[DocumentResponse]])
async def list_documents(
    user: Annotated[User, Depends(PermissionChecker("documents:read"))],
    skip: int = 0,
    limit: int = 100,
):
    async with async_session() as session:
        statement = (
            select(Document)
            .where(
                and_(
                    Document.user_id == user.id,
                    Document.deleted_at == None,  # noqa: E711
                )
            )
            .offset(skip)
            .limit(limit)
        )
        results = await session.execute(statement)
        documents = results.scalars().all()

    return SuccessResponse[List[DocumentResponse]](
        data=[DocumentResponse.model_validate(d) for d in documents],
        message="Documents retrieved successfully",
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
    await Document.objects.save(document)

    return SuccessResponse(message="Document deleted successfully")
