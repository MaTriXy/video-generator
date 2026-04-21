import sys
import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

# Clear SSLKEYLOGFILE if it points to an inaccessible path (e.g. AVG antivirus proxy)
_sslkeylog = os.environ.get("SSLKEYLOGFILE", "")
if _sslkeylog and not os.access(_sslkeylog, os.W_OK):
    os.environ.pop("SSLKEYLOGFILE", None)

from dotenv import load_dotenv
load_dotenv()

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from scripts.server_agents.video_step_agent_controller import VideoStepAgentController
from scripts.server_agents.video_update_backend_notifier import send_failure_to_backend
from scripts.server_agents.claude_sdk_config import ALLOWED_STEP_NAMES
from scripts.logging_config import get_service_logger

logger = get_service_logger("video_generation_server")


class VideoGenerationRequest(BaseModel):
    video_id: str
    step_type: str
    agent_id: Optional[str] = None
    resume_prompt: Optional[str] = None
    session_id: Optional[str] = None


class SceneRegenerationRequest(BaseModel):
    video_id: str
    scene_indices: List[int]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


async def run_query(step_type: str, video_id: str):
    logger.info(f"Starting query: step={step_type}", extra={"video_id": video_id, "step": step_type})
    try:
        await VideoStepAgentController.query(step_type, video_id)
        logger.info(f"Query completed: step={step_type}", extra={"video_id": video_id, "step": step_type})
    except Exception as e:
        error_msg = f"Error in {step_type} for {video_id}: {e}"
        logger.error(error_msg, exc_info=True, extra={"video_id": video_id, "step": step_type})
        await send_failure_to_backend(
            video_id=video_id,
            step_type=step_type,
            error_message=error_msg
        )


async def resume(step_type: str, video_id: str, agent_id: str, resume_prompt: str, session_id: Optional[str] = None):
    logger.info(f"Starting resume: agent={agent_id}, session={session_id}", extra={"video_id": video_id, "step": step_type})
    try:
        await VideoStepAgentController.resume(step_type, video_id, agent_id, resume_prompt, session_id)
        logger.info(f"Resume completed: agent={agent_id}", extra={"video_id": video_id, "step": step_type})
    except Exception as e:
        error_msg = f"Error resuming {agent_id} for {video_id}: {e}"
        logger.error(error_msg, exc_info=True, extra={"video_id": video_id, "step": step_type})
        await send_failure_to_backend(
            video_id=video_id,
            step_type=step_type,
            error_message=error_msg,
            session_id=session_id
        )


@app.post('/video-generation')
async def video_generation(request: VideoGenerationRequest):
    logger.info(f"Received request: step={request.step_type}, agent_id={request.agent_id}", extra={"video_id": request.video_id, "step": request.step_type})

    if request.step_type not in ALLOWED_STEP_NAMES:
        logger.error(f"Invalid step_type: {request.step_type}", extra={"video_id": request.video_id, "step": request.step_type})
        raise HTTPException(status_code=400, detail=f"step_type must be one of: {ALLOWED_STEP_NAMES}")

    try:
        if request.agent_id and request.resume_prompt:
            asyncio.create_task(resume(request.step_type, request.video_id, request.agent_id, request.resume_prompt, request.session_id))
            logger.info(f"Resume task dispatched: agent={request.agent_id}", extra={"video_id": request.video_id, "step": request.step_type})
            return {
                'status': 'resumed',
                'video_id': request.video_id,
                'agent_id': request.agent_id,
            }

        asyncio.create_task(run_query(request.step_type, request.video_id))
        logger.info(f"Query task dispatched: step={request.step_type}", extra={"video_id": request.video_id, "step": request.step_type})
        return {
            'status': 'started',
            'video_id': request.video_id,
            'step_type': request.step_type,
        }
    except ValueError as e:
        logger.error(f"Validation error: {e}", extra={"video_id": request.video_id, "step": request.step_type})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True, extra={"video_id": request.video_id, "step": request.step_type})
        raise HTTPException(status_code=500, detail=str(e))


async def run_scene_regeneration(video_id: str, scene_indices: List[int]):
    logger.info(f"Starting scene regeneration: scenes={scene_indices}", extra={"video_id": video_id, "step": "scene-regen"})
    try:
        from scripts.server_agents.scene_regeneration_controller import SceneRegenerationAgent
        agent = SceneRegenerationAgent(scene_indices)
        await agent.query_agent(video_id)
        logger.info(f"Scene regeneration completed: scenes={scene_indices}", extra={"video_id": video_id, "step": "scene-regen"})
    except Exception as e:
        error_msg = f"Error in scene regeneration for {video_id}: {e}"
        logger.error(error_msg, exc_info=True, extra={"video_id": video_id, "step": "scene-regen"})
        await send_failure_to_backend(
            video_id=video_id,
            step_type="code",
            error_message=error_msg
        )


@app.post('/scene-regeneration')
async def scene_regeneration(request: SceneRegenerationRequest):
    logger.info(f"Received scene regen request: scenes={request.scene_indices}", extra={"video_id": request.video_id, "step": "scene-regen"})

    if not request.scene_indices:
        raise HTTPException(status_code=400, detail="scene_indices must not be empty")

    try:
        asyncio.create_task(run_scene_regeneration(request.video_id, request.scene_indices))
        logger.info(f"Scene regen task dispatched: scenes={request.scene_indices}", extra={"video_id": request.video_id, "step": "scene-regen"})
        return {
            'status': 'started',
            'video_id': request.video_id,
            'scene_indices': request.scene_indices,
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True, extra={"video_id": request.video_id, "step": "scene-regen"})
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')
    uvicorn.run(app, host=host, port=port)
