# clear_pinecone.py
from app.config import settings
from pinecone import Pinecone

pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index(settings.PINECONE_INDEX_NAME)

# Delete all vectors in the index/namespace
index.delete(delete_all=True)
print("Pinecone index cleared successfully!")