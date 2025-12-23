"""API routers for camera management endpoints."""
import logging
from datetime import datetime
from typing import List
import uuid
from fastapi import APIRouter, HTTPException, status

from ..models import (
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraStatus,
    ErrorResponse
)
from ..config import settings
from ..database import database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(camera: CameraCreate):
    """
    Create and register a new camera in database.
    Camera is stored persistently in PostgreSQL.
    """
    try:
        camera_id = str(uuid.uuid4())
        created_at = datetime.now()
        
        # Insert into database
        query = """
            INSERT INTO cameras (id, name, rtsp_url, location, active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        
        location = camera.metadata.get('location', '') if camera.metadata else ''
        
        await database.execute(
            query,
            uuid.UUID(camera_id),
            camera.name,
            camera.source_url,
            location,
            camera.enabled,
            created_at,
            created_at
        )
        
        logger.info(f"Camera created in database: {camera_id} - {camera.name}")
        
        # Return response
        return CameraResponse(
            camera_id=camera_id,
            name=camera.name,
            source_type=camera.source_type,
            source_url=camera.source_url,
            enabled=camera.enabled,
            status=CameraStatus.INACTIVE if camera.enabled else CameraStatus.ERROR,
            frames_processed=0,
            last_frame_time=None,
            created_at=created_at,
            metadata=camera.metadata or {}
        )
    except Exception as e:
        logger.error(f"Failed to create camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create camera: {str(e)}"
        )


@router.get("/", response_model=List[CameraResponse])
async def list_cameras():
    """
    List all registered cameras from database.
    """
    try:
        query = """
            SELECT id, name, rtsp_url, location, active, created_at, updated_at
            FROM cameras
            ORDER BY created_at DESC
        """
        
        rows = await database.fetch_all(query)
        
        cameras = []
        for row in rows:
            cameras.append(CameraResponse(
                camera_id=str(row['id']),
                name=row['name'],
                source_type='webcam' if not row['rtsp_url'].startswith('rtsp') else 'rtsp',
                source_url=row['rtsp_url'],
                enabled=row['active'],
                status=CameraStatus.ACTIVE if row['active'] else CameraStatus.INACTIVE,
                frames_processed=0,
                last_frame_time=None,
                created_at=row['created_at'],
                metadata={'location': row['location'] or ''}
            ))
        
        return cameras
    except Exception as e:
        logger.error(f"Failed to list cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cameras: {str(e)}"
        )


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: str):
    """
    Get camera details by ID from database.
    """
    try:
        query = """
            SELECT id, name, rtsp_url, location, active, created_at, updated_at
            FROM cameras
            WHERE id = $1
        """
        
        row = await database.fetch_one(query, uuid.UUID(camera_id))
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {camera_id} not found"
            )
        
        return CameraResponse(
            camera_id=str(row['id']),
            name=row['name'],
            source_type='webcam' if not row['rtsp_url'].startswith('rtsp') else 'rtsp',
            source_url=row['rtsp_url'],
            enabled=row['active'],
            status=CameraStatus.ACTIVE if row['active'] else CameraStatus.INACTIVE,
            frames_processed=0,
            last_frame_time=None,
            created_at=row['created_at'],
            metadata={'location': row['location'] or ''}
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid camera ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera: {str(e)}"
        )


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
