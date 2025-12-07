"""API routers for camera management endpoints."""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, status

from ..models import (
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraStatus,
    ErrorResponse
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])

# In-memory storage for Sprint 1 (will use database in Sprint 2)
_cameras_db: dict = {}


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(camera: CameraCreate):
    """
    Create and register a new camera.
    
    For Sprint 1: Returns dummy data.
    Sprint 2: Will integrate with video-ingestion service.
    """
    camera_id = f"cam_{len(_cameras_db) + 1:03d}"
    
    camera_response = CameraResponse(
        camera_id=camera_id,
        name=camera.name,
        source_type=camera.source_type,
        source_url=camera.source_url,
        enabled=camera.enabled,
        status=CameraStatus.INACTIVE,
        frames_processed=0,
        last_frame_time=None,
        created_at=datetime.now(),
        metadata=camera.metadata
    )
    
    _cameras_db[camera_id] = camera_response
    
    logger.info(f"Camera created: {camera_id} - {camera.name}")
    
    return camera_response


@router.get("/", response_model=List[CameraResponse])
async def list_cameras():
    """
    List all registered cameras.
    
    For Sprint 1: Returns from in-memory storage.
    Sprint 2: Will query video-ingestion service.
    """
    return list(_cameras_db.values())


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: str):
    """
    Get camera details by ID.
    
    For Sprint 1: Returns from in-memory storage.
    Sprint 2: Will query video-ingestion service.
    """
    if camera_id not in _cameras_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found"
        )
    
    return _cameras_db[camera_id]


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: str, camera_update: CameraUpdate):
    """
    Update camera configuration.
    
    For Sprint 1: Updates in-memory storage.
    Sprint 2: Will update video-ingestion service.
    """
    if camera_id not in _cameras_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found"
        )
    
    camera = _cameras_db[camera_id]
    
    # Update fields
    if camera_update.name is not None:
        camera.name = camera_update.name
    if camera_update.enabled is not None:
        camera.enabled = camera_update.enabled
    if camera_update.metadata is not None:
        camera.metadata.update(camera_update.metadata)
    
    logger.info(f"Camera updated: {camera_id}")
    
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: str):
    """
    Delete camera.
    
    For Sprint 1: Removes from in-memory storage.
    Sprint 2: Will stop and remove from video-ingestion service.
    """
    if camera_id not in _cameras_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found"
        )
    
    del _cameras_db[camera_id]
    logger.info(f"Camera deleted: {camera_id}")
    
    return None
