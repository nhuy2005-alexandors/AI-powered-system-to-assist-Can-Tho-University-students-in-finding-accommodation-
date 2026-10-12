"""Native structured local judge with auditable outputs and bounded requests."""
import asyncio
import httpx
from ragas.llms.base import InstructorBaseRagasLLM


class OllamaRagasLLM(InstructorBaseRagasLLM):
    def __init__(self, url, model, max_output_tokens=8192, timeout_seconds=300):
        self.url = url.rstrip('/') + '/api/chat'
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.usage = []
        self.judgements = []

    def _body(self, prompt, response_model):
        print(f'Local judge: {len(prompt)} characters, schema: {response_model.__name__}', flush=True)
        return {'model': self.model, 'messages': [{'role': 'user', 'content': prompt}],
                'format': response_model.model_json_schema(), 'stream': False,
                'think': False, 'keep_alive': '30m',
                'options': {'temperature': 0, 'num_predict': self.max_output_tokens, 'num_ctx': 16384}}

    def _parse(self, response, response_model):
        response.raise_for_status()
        data = response.json()
        self.usage.append({key: data.get(key) for key in ('prompt_eval_count', 'eval_count', 'total_duration')})
        if data.get('done_reason') == 'length':
            raise RuntimeError('Local judge output reached token limit; score was not accepted')
        parsed = response_model.model_validate_json(data['message']['content'])
        self.judgements.append({'schema': response_model.__name__, 'output': parsed.model_dump(mode='json')})
        return parsed

    def generate(self, prompt, response_model):
        return self._parse(httpx.post(self.url, json=self._body(prompt, response_model),
                                     timeout=self.timeout_seconds), response_model)

    async def agenerate(self, prompt, response_model):
        async def request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                return self._parse(await client.post(self.url, json=self._body(prompt, response_model)), response_model)
        return await asyncio.wait_for(request(), timeout=self.timeout_seconds)
