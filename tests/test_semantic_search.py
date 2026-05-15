import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.search import semantic_search
from app.models.models import Document, Chunk, DocumentStatus, User
from app.models.dbmanager import async_engine

@pytest.fixture
async def session():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()

@pytest.mark.asyncio
async def test_semantic_search_success(session: AsyncSession):
    # Skip if not postgres (vector operators don't work in sqlite)
    if "postgresql" not in str(async_engine.url):
        pytest.skip("Semantic search tests require PostgreSQL with pgvector")

    # 1. Setup test data
    user = User(username="testsearch", email="testsearch@example.com", password_hash="hash")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    doc = Document(
        user_id=user.id,
        title="Search Test Doc",
        filename="test.txt",
        content=b"content",
        status=DocumentStatus.READY.value
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    
    # Add chunks with embeddings
    # Using 768 dimensions to match migration dc959ae8f0a6
    vec1 = [0.0] * 768
    vec1[0] = 1.0
    vec2 = [0.0] * 768
    vec2[1] = 1.0
    
    c1 = Chunk(document_id=doc.id, index=0, content="Apple is red", embedding=vec1)
    c2 = Chunk(document_id=doc.id, index=1, content="Banana is yellow", embedding=vec2)
    session.add_all([c1, c2])
    await session.commit()

    # 2. Mock embedding generation for query
    query = "red fruit"
    mock_embedding = [0.0] * 768
    mock_embedding[0] = 0.9
    mock_embedding[1] = 0.1
    
    with patch("app.services.search.generate_embedding_cached", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_embedding
        
        results = await semantic_search(
            query=query,
            user_id=user.id,
            session=session,
            min_score=0.1
        )
        
        assert len(results) > 0
        assert "Apple" in results[0].content
        assert results[0].document_title == "Search Test Doc"
        assert results[0].score > 0.8

@pytest.mark.asyncio
async def test_semantic_search_filters_by_user(session: AsyncSession):
    if "postgresql" not in str(async_engine.url):
        pytest.skip("Semantic search tests require PostgreSQL with pgvector")

    # Setup two users
    u1 = User(username="u1", email="u1@example.com", password_hash="hash")
    u2 = User(username="u2", email="u2@example.com", password_hash="hash")
    session.add_all([u1, u2])
    await session.commit()
    
    doc1 = Document(user_id=u1.id, title="U1 Doc", filename="u1.txt", content=b"c", status=DocumentStatus.READY.value)
    doc2 = Document(user_id=u2.id, title="U2 Doc", filename="u2.txt", content=b"c", status=DocumentStatus.READY.value)
    session.add_all([doc1, doc2])
    await session.commit()
    
    vec = [0.0] * 768
    vec[0] = 1.0
    
    c1 = Chunk(document_id=doc1.id, index=0, content="U1 Content", embedding=vec)
    c2 = Chunk(document_id=doc2.id, index=0, content="U2 Content", embedding=vec)
    session.add_all([c1, c2])
    await session.commit()

    with patch("app.services.search.generate_embedding_cached", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = vec
        
        # Search as U1
        results = await semantic_search(query="test", user_id=u1.id, session=session)
        assert len(results) == 1
        assert results[0].content == "U1 Content"
        
        # Search as U2
        results = await semantic_search(query="test", user_id=u2.id, session=session)
        assert len(results) == 1
        assert results[0].content == "U2 Content"
