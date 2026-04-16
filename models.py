import uuid
from typing import List
from sqlmodel import Field, SQLModel, Relationship


class User(SQLModel, table=True):
    """User model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    username: str = Field(index=True)
    email: str = Field(unique=True)
    password_hash: str
    tier: str = Field(default="free")
    tokens_used: int = Field(default=0)
    token_limit: int = Field(default=10000)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    documents: List["Document"] = Relationship(back_populates="user")
    conversations: List["Conversation"] = Relationship(back_populates="user")
    usage_logs: List["UsageLog"] = Relationship(back_populates="user")


class Role(SQLModel, table=True):
    """Role model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    name: str = Field(index=True, unique=True)
    description: str | None = None
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)

    users: List["User"] = Relationship(back_populates="role")
    permissions: List["RolePermission"] = Relationship(back_populates="role")


class Permission(SQLModel, table=True):
    """Permission model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    name: str = Field(index=True, unique=True)
    description: str | None = None
    resource: str
    action: str
    created_at: datetime = Field(default_factory=datetime.now)

    roles: List["RolePermission"] = Relationship(back_populates="permissions")


class UserRole(SQLModel, table=True):
    """UserRole model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE")
    role_id: uuid.UUID = Field(index=True, foreign_key="role.id", nullable=False, ondelete="CASCADE")
    assigned_by: uuid.UUID | None = Field(index=True, foreign_key="user.id", nullable=True, ondelete="SET NULL")
    assigned_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="roles")
    role: Role = Relationship(back_populates="users")


class RolePermission(SQLModel, table=True):
    """RolePermission model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    role_id: uuid.UUID = Field(index=True, foreign_key="role.id", nullable=False, ondelete="CASCADE")
    permission_id: uuid.UUID = Field(index=True, foreign_key="permission.id", nullable=False, ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.now)

    role: Role = Relationship(back_populates="permissions")
    permission: Permission = Relationship(back_populates="roles")


class Document(SQLModel, table=True):
    """Document model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE")
    title: str
    filename: str
    content: str
    mime_type: str | None = None
    file_size_bytes: int | None = None
    chunk_count: int = Field(default=0)
    status: str = Field(default="pending")
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="documents")
    chunks: List["Chunk"] = Relationship(back_populates="document")
    messages: List["Message"] = Relationship(back_populates="document")


class Chunk(SQLModel, table=True):
    """Chunk model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    document_id: uuid.UUID = Field(index=True, foreign_key="document.id", nullable=False, ondelete="CASCADE")
    index: int = Field(index=True)
    content: str
    token_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)

    document: Document = Relationship(back_populates="chunks")

    
class Conversation(SQLModel, table=True):
    """Conversation model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE")
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")

class Message(SQLModel, table=True):
    """Message model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    conversation_id: uuid.UUID = Field(index=True, foreign_key="conversation.id", nullable=False, ondelete="CASCADE")
    document_id: uuid.UUID = Field(index=True, foreign_key="document.id", nullable=True, ondelete="SET NULL")
    role: str
    content: str
    sources: str | None = None
    confidence: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    conversation: Conversation = Relationship(back_populates="messages")
    document: Document | None = Relationship(back_populates="messages")

class UsageLog(SQLModel, table=True):
    """UsageLog model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE")
    action: str
    tokens: int
    cost_usd: float
    metadata: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="usage_logs")
    

class AITrace(SQLModel, table=True):
    """AITrace model
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    trace_id: str = Field(index=True, unique=True, nullable=False)
    user_id: uuid.UUID = Field(index=True, foreign_key="user.id", nullable=True, ondelete="SET NULL")
    operation: str
    data: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="ai_traces")
