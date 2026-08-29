from app.knowledge.parser import ParsedBlock, parser_service


def test_chunk_overlap_and_content():
    original_size = parser_service.settings.chunk_size
    original_overlap = parser_service.settings.chunk_overlap
    try:
        parser_service.settings.chunk_size = 100
        parser_service.settings.chunk_overlap = 20
        chunks = parser_service.chunk([ParsedBlock("A" * 250, 3)])
        assert len(chunks) >= 3
        assert all(chunk.page_number == 3 for chunk in chunks)
        assert all(chunk.text for chunk in chunks)
    finally:
        parser_service.settings.chunk_size = original_size
        parser_service.settings.chunk_overlap = original_overlap
