from app.services.genai_processors import Processor
from app.services.pubsub import publish_task_message

class SampleProcessor(Processor):
    async def process(self, task_uuid, repo_dir, task_name, result, prompt):
        await publish_task_message(task_uuid, "[sample] SampleProcessor running")
        # Example: normalize whitespace on result if string
        if isinstance(result, str):
            result = " ".join(result.split())
        return {"result": result, "sample_processed": True}
