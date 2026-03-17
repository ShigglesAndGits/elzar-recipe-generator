import json
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional

from ..models import IdeaCreate, IdeaUpdate, IdeaResponse
from ..database import db

router = APIRouter(prefix="/api/ideas", tags=["ideas"])


def _to_response(idea: dict) -> IdeaResponse:
    tags = idea.get("tags", "[]")
    if isinstance(tags, str):
        tags = json.loads(tags)
    return IdeaResponse(
        id=idea["id"],
        name=idea["name"],
        notes=idea.get("notes", ""),
        tags=tags,
        calorie_estimate=idea.get("calorie_estimate"),
        status=idea.get("status", "idea"),
        created_at=idea["created_at"],
        updated_at=idea["updated_at"],
    )


@router.post("/", response_model=IdeaResponse)
async def create_idea(request: IdeaCreate):
    """Create a new idea"""
    idea_id = await db.create_idea({
        "name": request.name,
        "notes": request.notes,
        "tags": request.tags,
        "calorie_estimate": request.calorie_estimate,
        "status": request.status,
    })
    idea = await db.get_idea(idea_id)
    return _to_response(idea)


@router.get("/", response_model=List[IdeaResponse])
async def get_ideas(
    status: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
):
    """Get ideas with optional filtering by status, search text, or tag"""
    ideas = await db.get_ideas(status=status, search=search, tag=tag)
    return [_to_response(i) for i in ideas]


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(idea_id: int):
    """Get a specific idea"""
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Idea not found"
        )
    return _to_response(idea)


@router.put("/{idea_id}", response_model=IdeaResponse)
async def update_idea(idea_id: int, request: IdeaUpdate):
    """Update an idea"""
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    success = await db.update_idea(idea_id, update_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Idea not found"
        )

    idea = await db.get_idea(idea_id)
    return _to_response(idea)


@router.delete("/{idea_id}")
async def delete_idea(idea_id: int):
    """Delete an idea"""
    success = await db.delete_idea(idea_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Idea not found"
        )
    return {"status": "success", "message": "Idea deleted"}
