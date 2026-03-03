from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4, UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Annotated

from app.db import get_db, Base, engine, User
from app.schema import (
    UserCreate,
    UserResponse
)

# Create all tables
Base.metadata.create_all(bind=engine)

router = APIRouter()

# Define a dependency type alias
DatabaseSession = Annotated[Session, Depends(get_db)]

@router.post(
    "/users/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user"
)
def create_user(
    user: UserCreate,
    session: DatabaseSession
):
    """
    Create a new user.
    
    Parameters:
    - **email**: User's email (must be unique)
    - **notion_database_id**: Notion database ID
    - **notion_api_key**: Notion API key
    """
    # Create new user
    db_user = User(
        id=uuid4(),
        email=user.email,
        notion_database_id=user.notion_database_id,
        notion_api_key=user.notion_api_key
    )

    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)  # Optional: refresh to get DB-generated values
        return db_user  # ← ADD THIS!
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig).lower()
        print(f"IntegrityError: {error_msg}")  # Debug log
        
        if 'email' in error_msg or 'unique' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{user.email}' already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )


@router.get(
    "/users/",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get All Users",
    description="Retrieve all users"
)
def get_users(session: DatabaseSession):
    """
    Retrieve all users.
    """
    users = session.query(User).all()
    return users


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User",
    description="Retrieve a specific user by ID"
)
def get_user(
    user_id: UUID,
    session: DatabaseSession
):
    """
    Retrieve a single user by ID.
    """
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found"
        )
    
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User",
    description="Delete a user"
)
def delete_user(
    user_id: UUID,
    session: DatabaseSession
):
    """
    Delete a user.
    Note: This will also delete all their assets due to cascade.
    """
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found"
        )
    
    try:
        session.delete(user)
        session.commit()
        return None
        
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )