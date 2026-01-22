from typing import List, Tuple

def chunk_pages(pages: List[str], chunk_size: int = 900, chunk_overlap: int = 150) -> List[str]:
    chunks: List[str] = []
    
    full_text = " ".join(pages)
    text_length = len(full_text)
    
    if text_length == 0:
        return chunks
    
    start = 0
    while start < text_length:
        # Calculate end position
        end = min(start + chunk_size, text_length)

        # Extract chunk
        chunk = full_text[start:end].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)

        # If this was the last chunk (we reached the end), break
        if end >= text_length:
            break
        
        # Calculate next starting position
        start = end - chunk_overlap
    
    return chunks