import pymupdf as fitz
import os
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

class PDFProcessor:
    def __init__(self, output_screenshot_dir: str = "data/screenshots"):
        self.output_dir = output_screenshot_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 500 characters (~100 words) per chunk gives precise vector matches
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )

    def process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")

        doc = fitz.open(pdf_path)
        pdf_filename = os.path.basename(pdf_path)

        # Step 1: Render page screenshots first
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            image_filename = f"{os.path.splitext(pdf_filename)[0]}_page_{page_num + 1}.png"
            pix.save(os.path.join(self.output_dir, image_filename))

        # Step 2: Extract text per page and build granular page-aware chunks
        extracted_chunks = []
        global_chunk_idx = 1

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if not text:
                continue

            # Split page text into granular semantic units
            sub_chunks = self.text_splitter.split_text(text)
            image_filename = f"{os.path.splitext(pdf_filename)[0]}_page_{page_num + 1}.png"
            image_path = os.path.join(self.output_dir, image_filename)

            for sub_idx, chunk_text in enumerate(sub_chunks):
                extracted_chunks.append({
                    "chunk_id": f"{pdf_filename}_c{global_chunk_idx}",
                    "text": chunk_text,
                    "metadata": {
                        "document_title": pdf_filename,
                        "page_number": page_num + 1,
                        "chunk_index": sub_idx + 1,
                        "screenshot_path": image_path,
                        "total_pages": len(doc)
                    }
                })
                global_chunk_idx += 1

        print(f"--- Extracted {len(extracted_chunks)} granular chunks from {len(doc)} pages ---")
        return extracted_chunks

# Provide both names to prevent any import mismatches across modules
pdf_processor_service = PDFProcessor()
pdf_processor = pdf_processor_service