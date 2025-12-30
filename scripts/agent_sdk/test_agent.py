import asyncio
import json
from pprint import pprint
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage
from datetime import datetime

class CostTracker:
    def __init__(self):
        self.processed_message_ids = set()
        self.step_usages = []
        self.msg_count=0

    def message_to_dict(self, message):
        """Convert message object to JSON-serializable dict"""
        if hasattr(message, 'model_dump'):
            return message.model_dump()
        elif hasattr(message, '__dict__'):
            # Manually extract attributes
            result = {}
            for key, value in message.__dict__.items():
                if key.startswith('_'):
                    continue
                try:
                    json.dumps(value)  # Test if serializable
                    result[key] = value
                except (TypeError, ValueError):
                    result[key] = str(value)
            return result
        else:
            return str(message)

    async def track_conversation(self, prompt, options=None):
        result = None

        # Process messages as they arrive
        try:
            async for message in query(prompt=prompt, options=options):
                try:
                    self.process_message(message)

                    # Print each message for debugging
                    print("\n" + "-" * 80)
                    # pprint(message)
                    print(f"Message {self.msg_count}:")
                    self.msg_count+=1
                    print(json.dumps(self.message_to_dict(message), indent=2))
                    # Log usage tokens if available
                    if hasattr(message, 'usage'):
                        print("\n" + "*" * 80 + "Usage Tokens" + "*" * 80)
                        print("\nUsage Tokens:",json.dumps(message.usage, indent=2))

                    if isinstance(message, AssistantMessage) and hasattr(message, 'usage'):
                        print(f"  Input tokens: {message.usage.get('input_tokens', 0)}")
                        # print(f"  Output tokens: {message.usage.get('output_tokens', 0)}")
                        # print(f"  Cache creation tokens: {message.usage.get('cache_creation_input_tokens', 0)}")
                        # print(f"  Cache read tokens: {message.usage.get('cache_read_input_tokens', 0)}")
                        # print(f"  Total tokens: {sum(message.usage.values())}")
                    print("-" * 80)

                    # Capture the final result message
                    if isinstance(message, ResultMessage):
                        result = message
                except Exception as e:
                    print(f"Error processing message: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"Error in query loop: {e}")
            import traceback
            traceback.print_exc()

        return {
            "result": result,
            "step_usages": self.step_usages,
            "total_cost": result.total_cost_usd if result else 0
        }

    def process_message(self, message):
        # Only process assistant messages with usage
        if not isinstance(message, AssistantMessage) or not hasattr(message, 'usage'):
            return

        # Skip if already processed this message ID
        message_id = getattr(message, 'id', None)
        if not message_id or message_id in self.processed_message_ids:
            return

        # Mark as processed and record usage
        self.processed_message_ids.add(message_id)
        self.step_usages.append({
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "usage": message.usage,
            "cost_usd": self.calculate_cost(message.usage)
        })

    def calculate_cost(self, usage):
        # Implement your pricing calculation
        input_cost = usage.get("input_tokens", 0) * 0.00003
        output_cost = usage.get("output_tokens", 0) * 0.00015
        cache_creation_cost = usage.get("cache_creation_input_tokens", 0) * 0.0000375
        cache_read_cost = usage.get("cache_read_input_tokens", 0) * 0.0000075

        return input_cost + output_cost + cache_creation_cost + cache_read_cost

async def main():
    # prompt=f'Run this bash command: python .claude/skills/video-creator/scripts/path_manager.py --topic {topic} --asset-type "Design" --scene-index 0 --subpath "latest" --quiet'
    prompt="use the asset-creator skill and save a .svg file in root folder. the svg will be of a sun."
    # prompt="what is 1+1?"
    skill_options = ClaudeAgentOptions(
        setting_sources=["project"],  # Load Skills from filesystem
        allowed_tools=["Skill", "Read", "Write", "Bash", "Edit"]
    )

    topic = "sample_topic"  # Replace with your desired topic

    # Initialize cost tracker and run the conversation
    tracker = CostTracker()
    result = await tracker.track_conversation(prompt, options=skill_options)

    # Print cost summary with pretty formatting
    print("\n" + "="*80)
    print("COST TRACKING SUMMARY")
    print("="*80)
    print(f"Steps processed: {len(result['step_usages'])}")
    print(f"Total cost: ${result['total_cost']:.4f}")

    # Print detailed usage per step with pretty printing
    if result['step_usages']:
        print("\nDetailed usage per step:")
        for i, step in enumerate(result['step_usages'], 1):
            print(f"\n{'-' * 60}")
            print(f"Step {i}:")
            print('-' * 60)
            pprint(step, indent=2, width=100)
    print("="*80)

asyncio.run(main())
