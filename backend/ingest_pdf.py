import os
import pypdf
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings

def ingest_pdf_with_table_context(pdf_path: str):
    """
    Extracts text page-by-page from PDF, attaches page numbers and document context,
    and indexes table-aware chunks into Pinecone.
    """
    print(f"--- Starting Ingestion for: {pdf_path} ---")
    
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found!")
        return

    reader = pypdf.PdfReader(pdf_path)
    filename = os.path.basename(pdf_path)
    
    documents = []
    
    for idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        if not raw_text.strip():
            continue
            
        # Prepend explicit structural context headers to preserve layout info
        structured_text = (
            f"[Document: {filename} | Page Number: {idx}]\n"
            f"--- Page {idx} Content ---\n"
            f"{raw_text}"
        )
        
        documents.append({
            "page_number": idx,
            "text": structured_text,
            "filename": filename,
            "screenshot_path": f"/screenshots/{os.path.splitext(filename)[0]}_page_{idx}.png"
        })

    # Chunk text while preserving page headers
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = []
    for doc in documents:
        splits = text_splitter.split_text(doc["text"])
        for chunk_idx, split_text in enumerate(splits):
            chunk_with_header = f"[Page {doc['page_number']}]\n{split_text}"
            chunks.append({
                "id": f"{filename}_p{doc['page_number']}_c{chunk_idx}",
                "text": chunk_with_header,
                "metadata": {
                    "text": chunk_with_header,
                    "page_number": doc["page_number"],
                    "filename": doc["filename"],
                    "screenshot_path": doc["screenshot_path"]
                }
            })

    print(f"--- Generated {len(chunks)} table-aware chunk(s) across {len(documents)} page(s) ---")

    # Configure embeddings to use OpenRouter base_url when an OpenRouter key is provided
    api_key = settings.OPENAI_API_KEY or settings.OPENROUTER_API_KEY
    is_openrouter = settings.OPENROUTER_API_KEY and not settings.OPENAI_API_KEY

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1" if is_openrouter else None
    )
    
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)

    vectors_to_upsert = []
    for chunk in chunks:
        vector = embeddings.embed_query(chunk["text"])
        vectors_to_upsert.append((chunk["id"], vector, chunk["metadata"]))

    # Upsert in batches of 50
    batch_size = 50
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"Upserted batch {i // batch_size + 1}")

    print("--- Ingestion Complete! Document is ready for querying. ---")

if __name__ == "__main__":
    # Ensure this matches your directory path (data/pdfs/sample_doc.pdf)
    ingest_pdf_with_table_context("data/pdfs/sample_doc.pdf")