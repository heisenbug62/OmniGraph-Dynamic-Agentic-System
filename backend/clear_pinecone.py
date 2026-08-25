import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is not set in .env")

if not PINECONE_INDEX_NAME:
    raise ValueError("PINECONE_INDEX_NAME is not set in .env")

# Connect to Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Connect to your index
index = pc.Index(PINECONE_INDEX_NAME)

# Show current stats
print("Before deletion:")
print(index.describe_index_stats())

# Delete ALL vectors
index.delete(delete_all=True)

print("\nAll vectors deleted successfully.")

# Check stats again
print("\nAfter deletion:")
print(index.describe_index_stats())