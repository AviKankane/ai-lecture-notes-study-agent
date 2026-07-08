from app.services.chunking import count_words, split_text_into_chunks


def test_count_words():
    assert count_words("one two three") == 3


def test_split_text_into_chunks_small_text():
    chunks = split_text_into_chunks("word " * 120)
    assert len(chunks) == 1
    assert chunks[0].word_count == 120


def test_split_text_into_chunks_large_text():
    chunks = split_text_into_chunks("word " * 700)
    assert len(chunks) >= 2
    assert all(chunk.word_count <= 400 for chunk in chunks)
