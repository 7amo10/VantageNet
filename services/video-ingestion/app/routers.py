"""
API routes for camera management
"""
import logging
import asyncio
from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models import (
    CameraCreate,
    CameraResponse,
    CameraListResponse,
    ErrorResponse
)
from app.camera_manager import camera_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new camera"
)
async def create_camera(camera: CameraCreate):
    """
    Register a new camera and start capturing frames.
    
    - **name**: Descriptive name for the camera
    - **source_type**: Type of source (rtsp, webcam, file)
    - **source_url**: RTSP URL, webcam index (e.g., "0"), or file path
    - **fps**: Target frames per second (default: 10)
    - **enabled**: Whether to start capture immediately (default: true)
    - **metadata**: Additional camera metadata
    """
    try:
        video_capture = await camera_manager.add_camera(camera)
        return CameraResponse(**video_capture.to_dict())
    except Exception as e:
        logger.error(f"Failed to create camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create camera: {str(e)}"
        )


@router.get(
    "",
    response_model=CameraListResponse,
    summary="List all cameras"
)
async def list_cameras():
    """
    List all registered cameras with their current status.
    
    Returns information about all cameras including:
    - Current status (active, inactive, error, reconnecting)
    - Frames processed and dropped
    - Last frame timestamp
    """
    try:
        cameras = camera_manager.list_cameras()
        camera_responses = [CameraResponse(**cam.to_dict()) for cam in cameras]
        return CameraListResponse(
            cameras=camera_responses,
            total=len(camera_responses)
        )
    except Exception as e:
        logger.error(f"Failed to list cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cameras: {str(e)}"
        )


@router.get(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Get camera details"
)
async def get_camera(camera_id: str):
    """
    Get detailed information about a specific camera.
    """
    camera = camera_manager.get_camera(camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found"
        )
    
    return CameraResponse(**camera.to_dict())


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop and remove a camera"
)
async def delete_camera(camera_id: str):
    """
    Stop capturing from a camera and remove it from the system.
    """
    success = await camera_manager.remove_camera(camera_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found"
        )
    return None


@router.get(
    "/{camera_id}/stream",
    summary="Stream camera video (MJPEG)",
    response_class=StreamingResponse
)
async def stream_camera(camera_id: str, annotate: bool = True):
    """
    Stream video from a camera using MJPEG format.
    
    This endpoint provides a continuous MJPEG stream that can be
    displayed in browsers or consumed by video players.
    
    Args:
        annotate: If True, draw emotion detection boxes on the video (default: True)
    """
    from app.annotation_overlay import annotation_overlay
    
    camera = camera_manager.get_camera(camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found"
        )
    
    async def generate_frames():
        """Generator function that yields MJPEG frames with annotations"""
        try:
            while True:
                # Get current frame from camera
                frame_data = camera.get_latest_frame()
                
                if frame_data:
                    # Apply annotations if enabled
                    if annotate and annotation_overlay.connected:
                        frame_data = annotation_overlay.draw_annotations(frame_data, camera_id)
                    
                    # Yield frame in MJPEG format
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n'
                    )
                else:
                    # Camera not active or no frame available yet
                    await asyncio.sleep(0.1)
                    continue
                
                # Control frame rate (10 FPS)
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for camera {camera_id}")
        except Exception as e:
            logger.error(f"Error streaming camera {camera_id}: {e}")
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )
