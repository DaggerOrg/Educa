from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from cke.api.dependencies import get_qa_service
from cke.api.schemas.qa import AskRequest, AskResponse
from cke.services.qa_service import QAService

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest, service: Annotated[QAService, Depends(get_qa_service)]
) -> AskResponse:
    result = service.answer(request.question, course_id=request.course_id, top_k=request.top_k)
    return AskResponse.from_domain(result)
