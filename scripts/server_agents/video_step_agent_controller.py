from typing import Optional, Tuple, Any

from scripts.server_agents.base_persistent_agent import BasePersistentAgent
from scripts.server_agents.claude_sdk_config import get_asset_type_for_step, get_execution_type
from scripts.server_agents.execution_types import ExecutionType
from scripts.server_agents.step_execution_controllers.main_agent_execution import MainAgentExecution
from scripts.server_agents.step_execution_controllers.subagent_execution import SubagentExecution
from scripts.logging_config import get_service_logger

logger = get_service_logger("video_step_agent_controller")


def _create_agent(step_type: str) -> BasePersistentAgent:
    """Create the appropriate agent for the given step type."""
    asset_type = get_asset_type_for_step(step_type)
    execution_type = get_execution_type(asset_type)
    if execution_type == ExecutionType.MAIN_AGENT_EXECUTION:
        return MainAgentExecution(asset_type)
    return SubagentExecution(asset_type)


class VideoStepAgentController:

    @staticmethod
    async def query(step_type: str, video_id: str) -> Tuple[Any, int, str]:
        logger.info(f"Dispatching query to {step_type} agent", extra={"video_id": video_id, "step": step_type})
        agent = _create_agent(step_type)
        return await agent.query_agent(video_id)

    @staticmethod
    async def resume(step_type: str, video_id: str, agent_id: str, resume_prompt: str, session_id: Optional[str] = None) -> Tuple[Any, int, str]:
        logger.info(f"Dispatching resume to {step_type} agent: agent={agent_id}", extra={"video_id": video_id, "step": step_type})
        agent = _create_agent(step_type)
        return await agent.resume_agent(video_id, agent_id, resume_prompt, session_id)
