import uuid
from datetime import datetime
from typing import List, ClassVar
from sqlmodel import Field, SQLModel, Relationship

from dbmanager import QueryManager, UserManager

__all__ = [
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "Document",
    "Chunk",
    "Conversation",
    "Message",
    "UsageLog",
    "AITrace",
]


class User(SQLModel, table=True):
    """User model"""

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
    ai_traces: List["AITrace"] = Relationship(back_populates="user")
    roles: List["UserRole"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "UserRole.user_id"},
    )
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="user")

    @property
    def role_names(self) -> List[str]:
        try:
            return [ur.role.name for ur in self.roles if ur.role]
        except Exception:
            return []

    @property
    def permissions(self) -> set[str]:
        perms = set()
        try:
            for user_role in self.roles:
                if user_role.role:
                    for role_perm in user_role.role.permissions:
                        if role_perm.permission:
                            perms.add(role_perm.permission.name)
        except Exception:
            pass
        return perms

    objects: ClassVar[UserManager] = UserManager()


class Role(SQLModel, table=True):
    """Role model"""

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

    users: List["UserRole"] = Relationship(back_populates="role")
    permissions: List["RolePermission"] = Relationship(back_populates="role")

    objects: ClassVar[QueryManager] = QueryManager()


class Permission(SQLModel, table=True):
    """Permission model"""

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

    roles: List["RolePermission"] = Relationship(back_populates="permission")

    objects: ClassVar[QueryManager] = QueryManager()


class UserRole(SQLModel, table=True):
    """UserRole model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    role_id: uuid.UUID = Field(
        index=True, foreign_key="role.id", nullable=False, ondelete="CASCADE"
    )
    assigned_by: uuid.UUID | None = Field(
        index=True, foreign_key="user.id", nullable=True, ondelete="SET NULL"
    )
    is_default: bool = Field(default=False)
    assigned_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(
        back_populates="roles",
        sa_relationship_kwargs={"foreign_keys": "UserRole.user_id"},
    )
    role: Role = Relationship(back_populates="users")

    objects: ClassVar[QueryManager] = QueryManager()


class RolePermission(SQLModel, table=True):
    """RolePermission model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    role_id: uuid.UUID = Field(
        index=True, foreign_key="role.id", nullable=False, ondelete="CASCADE"
    )
    permission_id: uuid.UUID = Field(
        index=True, foreign_key="permission.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=datetime.now)

    role: Role = Relationship(back_populates="permissions")
    permission: Permission = Relationship(back_populates="roles")

    objects: ClassVar[QueryManager] = QueryManager()


class Document(SQLModel, table=True):
    """Document model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
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
    deleted_at: datetime | None = Field(default=None)

    user: User = Relationship(back_populates="documents")
    chunks: List["Chunk"] = Relationship(back_populates="document")
    messages: List["Message"] = Relationship(back_populates="document")

    objects: ClassVar[QueryManager] = QueryManager()


class Chunk(SQLModel, table=True):
    """Chunk model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    document_id: uuid.UUID = Field(
        index=True, foreign_key="document.id", nullable=False, ondelete="CASCADE"
    )
    index: int = Field(index=True)
    content: str
    token_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)

    document: Document = Relationship(back_populates="chunks")

    objects: ClassVar[QueryManager] = QueryManager()


class Conversation(SQLModel, table=True):
    """Conversation model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")

    objects: ClassVar[QueryManager] = QueryManager()


class Message(SQLModel, table=True):
    """Message model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    conversation_id: uuid.UUID = Field(
        index=True, foreign_key="conversation.id", nullable=False, ondelete="CASCADE"
    )
    document_id: uuid.UUID = Field(
        index=True, foreign_key="document.id", nullable=True, ondelete="SET NULL"
    )
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

    objects: ClassVar[QueryManager] = QueryManager()


class UsageLog(SQLModel, table=True):
    """UsageLog model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    action: str
    tokens: int
    cost_usd: float
    # In SQLModel and SQLAlchemy, the attribute name metadata is strictly reserved because it stores the central collection of Table objects and schema constructs for your database.
    log_metadata: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="usage_logs")

    objects: ClassVar[QueryManager] = QueryManager()


class AITrace(SQLModel, table=True):
    """AITrace model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    trace_id: str = Field(index=True, unique=True, nullable=False)
    user_id: uuid.UUID = Field(
        index=True, foreign_key="user.id", nullable=True, ondelete="SET NULL"
    )
    operation: str
    data: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="ai_traces")

    objects: ClassVar[QueryManager] = QueryManager()


class RefreshToken(SQLModel, table=True):
    """RefreshToken model"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        index=True, foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    token: str = Field(index=True, unique=True, nullable=False)
    is_revoked: bool = Field(default=False)
    is_used: bool = Field(default=False)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="refresh_tokens")

    objects: ClassVar[QueryManager] = QueryManager()
