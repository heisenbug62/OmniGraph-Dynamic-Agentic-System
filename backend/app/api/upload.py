from fastapi import APIRouter, File, File, Form, HTTPException
import shutil
import os
from pathlib import Path
from app.services.pdf_processor import pdf_processor
from app.services.vector_store import vector_store_service

router = APIRouter(prefix="/api", tags=["Document Ingestion"])

_DIR = Path("data/s")
_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/doc-status")
async def check_doc_status():
    """
    Called by frontend before  to check if a confirmation modal is needed.
    """
    has_docs = vector_store_service.has_existing_documents()
    return {"has_existing_documents": has_docs}


@router.post("/")
async def _document(
    file: File = File(...),
    replace_existing: bool = Form(default=False)
):
    """
    s, extracts text/screenshots, and indexes into Pinecone.
    - If replace_existing is True: Clears the previous index before upserting.
    - If replace_existing is False: Appends the new chunks alongside previous docs.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = _DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        if replace_existing:
            vector_store_service.clear_vectors()

        chunks = pdf_processor.process_pdf(str(file_path), filename=file.filename)
        vector_store_service.add_document_chunks(chunks)

        return {
            "status": "success",
            "message": f"Successfully indexed '{file.filename}'",
            "replace_existing": replace_existing,
            "total_chunks": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))