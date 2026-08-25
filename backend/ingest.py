#!/usr/bin/env python3
"""
ingest.py — Standalone Knowledge Base Ingestion Script
======================================================
One-time developer/admin script to ingest document(s) into Pinecone vector storage.

Usage Examples:
    # Ingest a single PDF:
    python ingest.py data/pdfs/sample_doc.pdf

    # Ingest an entire folder of PDFs:
    python ingest.py data/pdfs/

    # Wipe existing vectors in Pinecone and re-ingest fresh:
    python ingest.py data/pdfs/ --replace

    # Use default folder (data/pdfs):
    python ingest.py
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List

# Ensure backend root is on sys.path so app modules import cleanly
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.services.pdf_processor import PDFProcessor
from app.services.vector_store import vector_store_service


def find_pdf_files(target_path: Path) -> List[Path]:
    """Finds all PDF files given a file path or directory."""
    if not target_path.exists():
        print(f"❌ Error: Specified path does not exist: {target_path}")
        sys.exit(1)

    if target_path.is_file():
        if target_path.suffix.lower() == ".pdf":
            return [target_path]
        else:
            print(f"❌ Error: Specified file '{target_path.name}' is not a PDF.")
            sys.exit(1)

    # Search directory recursively for .pdf files
    pdf_files = sorted(
        [p for p in target_path.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"]
    )
    return pdf_files


def run_ingestion(target_path_str: str, replace: bool = False, screenshot_dir: str = None):
    """
    Processes PDF files, renders page screenshots, extracts semantic chunks,
    and upserts embeddings into Pinecone using the default namespace ("").
    """
    target_path = Path(target_path_str).resolve()
    
    print("=" * 65)
    print(" 🚀 OmniGraph Knowledge Base Ingestion Engine")
    print("=" * 65)
    print(f"📂 Target Source       : {target_path}")
    print(f"🌲 Pinecone Index      : {settings.PINECONE_INDEX_NAME}")
    print(f"🏷️  Namespace           : (default/root)")
    print(f"🔄 Replace Existing    : {'YES (Index will be cleared)' if replace else 'NO (Append mode)'}")
    print("=" * 65)

    pdf_files = find_pdf_files(target_path)
    if not pdf_files:
        print(f"⚠️  No PDF files found in '{target_path}'. Nothing to ingest.")
        return

    print(f"\n📄 Found {len(pdf_files)} PDF document(s) to process:")
    for idx, f in enumerate(pdf_files, 1):
        file_size_kb = f.stat().st_size / 1024
        print(f"   {idx}. {f.name} ({file_size_kb:.1f} KB)")

    # 1. Clear existing vectors if --replace was requested
    if replace:
        print("\n🗑️  [1/3] Clearing existing vectors from Pinecone...")
        vector_store_service.clear_vectors(namespace="")
        print("   ✅ Existing vectors cleared successfully.")
    else:
        print("\n⏩ [1/3] Skipping vector deletion (Append Mode active).")

    # 2. Initialize PDF processor and extract chunks & screenshots
    print("\n🔍 [2/3] Extracting text chunks and rendering citation screenshots...")
    processor = PDFProcessor(output_screenshot_dir=screenshot_dir)
    
    all_chunks = []
    total_pages = 0
    file_summaries = []

    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"   [{idx}/{len(pdf_files)}] Processing: {pdf_file.name} ...")
        try:
            chunks = processor.process_pdf(str(pdf_file))
            if chunks:
                pages_in_doc = chunks[0].get("metadata", {}).get("total_pages", 1)
                total_pages += pages_in_doc
            else:
                pages_in_doc = 0
            
            all_chunks.extend(chunks)
            file_summaries.append({
                "filename": pdf_file.name,
                "pages": pages_in_doc,
                "chunks": len(chunks)
            })
            print(f"       ↳ Extracted {len(chunks)} chunks across {pages_in_doc} pages.")
        except Exception as e:
            print(f"       ❌ Failed to process '{pdf_file.name}': {e}")

    if not all_chunks:
        print("\n⚠️  No text content or chunks could be extracted from the specified documents.")
        return

    # 3. Embed and upsert into Pinecone
    print(f"\n⚡ [3/3] Embedding {len(all_chunks)} chunks and upserting to Pinecone...")
    try:
        vector_store_service.add_document_chunks(all_chunks, namespace="")
        print("   ✅ All chunks successfully embedded and upserted to Pinecone!")
    except Exception as e:
        print(f"   ❌ Pinecone upsert failed: {e}")
        sys.exit(1)

    # Summary report
    print("\n" + "=" * 65)
    print(" 🎉 INGESTION SUMMARY REPORT")
    print("=" * 65)
    print(f" ✔️  Total PDF Files Processed : {len(pdf_files)}")
    print(f" ✔️  Total Pages Rendered       : {total_pages}")
    print(f" ✔️  Total Chunks Generated    : {len(all_chunks)}")
    print(f" ✔️  Vectors Upserted          : {len(all_chunks)}")
    print(f" ✔️  Target Pinecone Index     : {settings.PINECONE_INDEX_NAME}")
    print(f" ✔️  Screenshot Assets Dir     : {processor.output_dir}")
    print("=" * 65)
    print("✨ Ingestion complete! Knowledge base is live and ready for chat.")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="OmniGraph Knowledge Base Ingestion Script — extracts, embeds, and indexes PDFs into Pinecone."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(BACKEND_ROOT / "data" / "pdfs"),
        help="Path to a single PDF file or a directory containing PDFs (default: backend/data/pdfs)."
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Wipe all existing vectors in Pinecone before indexing new documents."
    )
    parser.add_argument(
        "--screenshot-dir",
        default=None,
        help="Optional custom output directory for citation screenshots (default: backend/data/screenshots)."
    )

    args = parser.parse_args()
    run_ingestion(
        target_path_str=args.path,
        replace=args.replace,
        screenshot_dir=args.screenshot_dir
    )


if __name__ == "__main__":
    main()
