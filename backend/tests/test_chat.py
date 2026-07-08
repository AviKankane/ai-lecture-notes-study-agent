from app.schemas import ChatResponse


def test_chat_response_shape():
    response = ChatResponse(answer="I don't know from the uploaded lectures.", citations=[])
    assert response.answer
    assert response.citations == []
