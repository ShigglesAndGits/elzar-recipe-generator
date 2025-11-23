from fastapi import APIRouter, HTTPException, status
from typing import List

from ..models import (
    DietaryProfileCreate,
    DietaryProfileUpdate,
    DietaryProfileResponse
)
from ..database import db

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.post("/", response_model=DietaryProfileResponse)
async def create_profile(profile: DietaryProfileCreate):
    """Create a new dietary profile for a household member"""
    try:
        profile_id = await db.create_profile(
            name=profile.name,
            dietary_restrictions=profile.dietary_restrictions
        )
        
        created_profile = await db.get_profile(profile_id)
        
        return DietaryProfileResponse(
            id=created_profile["id"],
            name=created_profile["name"],
            dietary_restrictions=created_profile["dietary_restrictions"],
            created_at=created_profile["created_at"],
            updated_at=created_profile["updated_at"]
        )
        
    except Exception as e:
        # Likely a duplicate name
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating profile: {str(e)}"
        )


@router.get("/", response_model=List[DietaryProfileResponse])
async def get_all_profiles():
    """Get all dietary profiles"""
    profiles = await db.get_all_profiles()
    
    return [
        DietaryProfileResponse(
            id=profile["id"],
            name=profile["name"],
            dietary_restrictions=profile["dietary_restrictions"],
            created_at=profile["created_at"],
            updated_at=profile["updated_at"]
        )
        for profile in profiles
    ]


@router.get("/{profile_id}", response_model=DietaryProfileResponse)
async def get_profile(profile_id: int):
    """Get a specific dietary profile"""
    profile = await db.get_profile(profile_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return DietaryProfileResponse(
        id=profile["id"],
        name=profile["name"],
        dietary_restrictions=profile["dietary_restrictions"],
        created_at=profile["created_at"],
        updated_at=profile["updated_at"]
    )


@router.put("/{profile_id}", response_model=DietaryProfileResponse)
async def update_profile(profile_id: int, update: DietaryProfileUpdate):
    """Update a dietary profile"""
    success = await db.update_profile(
        profile_id=profile_id,
        name=update.name,
        dietary_restrictions=update.dietary_restrictions
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    updated_profile = await db.get_profile(profile_id)
    
    return DietaryProfileResponse(
        id=updated_profile["id"],
        name=updated_profile["name"],
        dietary_restrictions=updated_profile["dietary_restrictions"],
        created_at=updated_profile["created_at"],
        updated_at=updated_profile["updated_at"]
    )


@router.delete("/{profile_id}")
async def delete_profile(profile_id: int):
    """Delete a dietary profile"""
    success = await db.delete_profile(profile_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return {"status": "success", "message": "Profile deleted"}

