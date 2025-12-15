from anthropic import NOT_GIVEN, APIStatusError, AsyncStream
from anthropic.types import TextBlockParam
from anthropic.types.beta import BetaMessage, BetaMessageParam, BetaRawMessageStreamEvent, BetaToolChoiceParam, BetaTextBlockParam
from pydantic_ai import ModelHTTPError
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import ModelRequestParameters, get_user_agent
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings

from scripts.logging_config import get_utility_logger
logger = get_utility_logger('llm_custom_models.anthropic')

PROMPT_CACHING_BETA_HEADER = "prompt-caching-2024-07-31"  # adjust if Anthropic bumps this

class AnthropicWithCache(AnthropicModel):
      """
      Custom AnthropicModel with caching:
      - System prompts: 1 hour cache
      - All other messages: 5 minute cache
      """

      async def _messages_create(
          self,
          messages: list[ModelMessage],
          stream: bool,
          model_settings: AnthropicModelSettings,
          model_request_parameters: ModelRequestParameters,
      ) -> BetaMessage | AsyncStream[BetaRawMessageStreamEvent]:

          logger.debug(f"inside AnthropicWithCache {messages}")

          # Get tools configuration
          tools = self._get_tools(model_request_parameters)
          builtin_tools_result = self._get_builtin_tools(model_request_parameters)

          # Handle case where _get_builtin_tools might return empty or unexpected result
          if not builtin_tools_result or len(builtin_tools_result) != 2:
              logger.warning(f"_get_builtin_tools returned unexpected result: {builtin_tools_result}")
              builtin_tools, tool_headers = [], {}
          else:
              builtin_tools, tool_headers = builtin_tools_result

          tools += builtin_tools

          tool_choice: BetaToolChoiceParam | None
          if not tools:
              tool_choice = None
          else:
              if not model_request_parameters.allow_text_output:
                  tool_choice = {'type': 'any'}
              else:
                  tool_choice = {'type': 'auto'}

              if (allow_parallel_tool_calls := model_settings.get('parallel_tool_calls')) is not None:
                  tool_choice['disable_parallel_tool_use'] = not allow_parallel_tool_calls

          # Get the original system prompt and messages with proper error handling
          logger.info(f"Processing {len(messages) if messages else 0} messages for caching")

          # Check if messages is empty or None
          if not messages:
              logger.warning("No messages provided to _messages_create")
              system_prompt_str = ""
              anthropic_messages = []
          else:
              try:
                  # Log message types for debugging
                  for i, msg in enumerate(messages):
                      logger.debug(f"Message {i}: type={type(msg)}, has content={hasattr(msg, 'content')}")

                  result = await super()._map_message(messages)
                  logger.info(f"Parent _map_message returned type: {type(result)}")

                  if not result:
                      logger.warning("Parent _map_message returned None or empty result")
                      system_prompt_str = ""
                      anthropic_messages = []
                  elif isinstance(result, tuple) and len(result) == 2:
                      system_prompt_str, anthropic_messages = result
                      logger.info(f"Got system prompt: {len(system_prompt_str) if system_prompt_str else 0} chars, messages: {len(anthropic_messages)}")
                  else:
                      logger.error(f"Unexpected result from parent _map_message: {type(result)} - {result}")
                      system_prompt_str = ""
                      anthropic_messages = []
              except ValueError as e:
                  if "not enough values to unpack" in str(e):
                      logger.error(f"Unpacking error - result was: {result if 'result' in locals() else 'not computed'}")
                      system_prompt_str = ""
                      anthropic_messages = []
                  else:
                      raise
              except Exception as e:
                  logger.error(f"Error calling parent _map_message: {e}")
                  import traceback
                  logger.error(traceback.format_exc())
                  raise

          # Convert system prompt to cached blocks with 1-hour TTL
          cached_system = None
          if system_prompt_str:
              cached_system = [
                  BetaTextBlockParam(
                      type="text",
                      text=system_prompt_str,
                      cache_control={"type": "ephemeral", "ttl": "1h"}  # 1-hour cache
                  )
              ]
              logger.info(f"Caching system prompt (1h): {len(system_prompt_str)} chars")

          # Add 5-minute cache to all messages (user and assistant)
          if anthropic_messages and len(anthropic_messages) > 0:
              for idx, msg in enumerate(anthropic_messages):
                  content = msg.get('content')
                  role = msg.get('role', 'unknown')

                  if isinstance(content, str) and len(content) > 100:  # Only cache if substantial
                      anthropic_messages[idx]['content'] = [
                          BetaTextBlockParam(
                              type="text",
                              text=content,
                              cache_control={"type": "ephemeral", "ttl": "5m"}  # 5-minute cache
                          )
                      ]
                      logger.info(f"Caching {role} message (5m): {len(content)} chars")
                  elif isinstance(content, list):
                      # Handle list of content blocks
                      cached_content = []
                      for item in content:
                          if isinstance(item, dict) and item.get('type') == 'text':
                              text = item.get('text', '')
                              if len(text) > 100:  # Cache substantial text blocks
                                  cached_item = BetaTextBlockParam(
                                      type="text",
                                      text=text,
                                      cache_control={"type": "ephemeral", "ttl": "5m"}
                                  )
                                  cached_content.append(cached_item)
                                  logger.info(f"Caching {role} content block (5m): {len(text)} chars")
                              else:
                                  cached_content.append(item)
                          else:
                              cached_content.append(item)

                      if cached_content:
                          anthropic_messages[idx]['content'] = cached_content

          try:
              # Setup headers with beta header for 1-hour TTL support
              extra_headers = model_settings.get('extra_headers', {})
              extra_headers['anthropic-beta'] = 'extended-cache-ttl-2025-04-11'
              for k, v in tool_headers.items():
                  extra_headers.setdefault(k, v)
              extra_headers.setdefault('User-Agent', get_user_agent())

              logger.info(f"Making API call with beta headers for extended TTL")

              # Use beta client for 1-hour cache support
              response = await self.client.beta.messages.create(
                  max_tokens=model_settings.get('max_tokens', 4096),
                  system=cached_system or system_prompt_str or NOT_GIVEN,  # Use cached or original
                  messages=anthropic_messages,
                  model=self._model_name,
                  tools=tools or NOT_GIVEN,
                  tool_choice=tool_choice or NOT_GIVEN,
                  stream=stream,
                  thinking=model_settings.get('anthropic_thinking', NOT_GIVEN),
                  stop_sequences=model_settings.get('stop_sequences', NOT_GIVEN),
                  temperature=model_settings.get('temperature', NOT_GIVEN),
                  top_p=model_settings.get('top_p', NOT_GIVEN),
                  timeout=model_settings.get('timeout', NOT_GIVEN),
                  metadata=model_settings.get('anthropic_metadata', NOT_GIVEN),
                  extra_headers=extra_headers,
                  extra_body=model_settings.get('extra_body'),
              )

              # Log cache statistics if available
              if not stream and hasattr(response, 'usage'):
                  usage = response.usage
                  if hasattr(usage, 'cache_creation_input_tokens'):
                      cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)
                      if cache_creation > 0:
                          logger.info(f"📝 Cache WRITE: {cache_creation} tokens cached")

                  if hasattr(usage, 'cache_read_input_tokens'):
                      cache_read = getattr(usage, 'cache_read_input_tokens', 0)
                      if cache_read > 0:
                          logger.info(f"✅ Cache HIT: {cache_read} tokens read from cache")
                          # Cache reads are ~90% cheaper
                          savings = cache_read * 0.9
                          logger.info(f"💰 Estimated savings: ~{savings:.0f} tokens worth")

              return response

          except APIStatusError as e:
              if (status_code := e.status_code) >= 400:
                  raise ModelHTTPError(status_code=status_code, model_name=self.model_name, body=e.body) from e
              raise
