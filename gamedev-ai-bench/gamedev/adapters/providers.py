"""Provider-specific HTTP adapters. No automatic routing, hidden retries, or paid discovery.

No provider was invoked during development. HTTP contracts are exercised against
strict mocked transports; live credentials are required for qualification.
"""
from dataclasses import dataclass
from urllib.parse import urlparse, quote
import json
import os
import httpx

ALLOWED_HOSTS = {'api.openai.com','api.anthropic.com','generativelanguage.googleapis.com',
                 'api.deepseek.com','dashscope-intl.aliyuncs.com','api.z.ai','api.moonshot.ai'}


class ProviderError(RuntimeError):
    def __init__(self, code: str, *, outcome_unknown: bool = False, retry_after: str | None = None):
        super().__init__(code)
        self.code = code
        self.outcome_unknown = outcome_unknown
        self.retry_after = retry_after


@dataclass
class Generation:
    text: str
    model_reported: str | None
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None
    usage: dict
    stop_reason: str | None = None


class ProviderAdapter:
    def __init__(self, provider, client: httpx.Client | None = None):
        self.provider = provider
        parsed = urlparse(provider.base_url)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.query:
            raise ValueError('Provider endpoint is not on the reviewed HTTPS allowlist')
        self.base = provider.base_url.rstrip('/')
        self.key = os.environ.get(provider.key_env, '')
        self.client = client or httpx.Client(timeout=httpx.Timeout(90, connect=10), follow_redirects=False,
                                             limits=httpx.Limits(max_connections=2))
        self.owned_client = client is None

    def close(self):
        if self.owned_client:
            self.client.close()

    def headers(self) -> dict:
        if not self.key:
            raise ProviderError('provider_not_configured')
        if self.provider.adapter == 'anthropic_messages':
            return {'x-api-key':self.key,'anthropic-version':'2023-06-01','content-type':'application/json'}
        if self.provider.adapter == 'gemini':
            return {'x-goog-api-key':self.key,'content-type':'application/json'}
        return {'Authorization':f'Bearer {self.key}','content-type':'application/json'}

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            # Never retry generation: a timeout can occur after the provider billed it.
            with self.client.stream(method, self.base+path, headers=self.headers(), json=payload) as response:
                if response.status_code >= 300:
                    code = 'rate_limited' if response.status_code == 429 else f'provider_http_{response.status_code}'
                    raise ProviderError(code, retry_after=response.headers.get('retry-after'))
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 4_000_000:
                        raise ProviderError('provider_response_too_large', outcome_unknown=method == 'POST')
            return json.loads(data)
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise ProviderError('provider_network_outcome_unknown', outcome_unknown=method == 'POST') from error
        except (ValueError, json.JSONDecodeError) as error:
            raise ProviderError('invalid_provider_json', outcome_unknown=method == 'POST') from error

    def list_models(self) -> list[dict]:
        items = []
        cursor = None
        for _ in range(20):
            if self.provider.adapter == 'gemini':
                path = '/models?pageSize=100' + (f'&pageToken={quote(cursor)}' if cursor else '')
            elif self.provider.adapter == 'anthropic_messages':
                path = '/models?limit=100' + (f'&after_id={quote(cursor)}' if cursor else '')
            else:
                path = '/models'
            data = self.request('GET', path)
            batch = data.get('models', data.get('data', []))
            if not isinstance(batch, list):
                raise ProviderError('invalid_model_catalog')
            for row in batch:
                api_id = str(row.get('id') or row.get('name', '')).removeprefix('models/')
                if api_id and len(api_id) <= 150:
                    items.append({'api_id':api_id,'display_name':str(row.get('display_name') or row.get('displayName') or api_id)[:150]})
            cursor = data.get('nextPageToken') or (data.get('last_id') if data.get('has_more') else None)
            if not cursor:
                break
        else:
            raise ProviderError('model_catalog_pagination_limit')
        return items

    def generate(self, model: str, system: str, prompt: str, max_output_tokens: int,
                 reasoning: str = 'provider-default') -> Generation:
        if not 128 <= max_output_tokens <= 32768 or len(prompt.encode()) > 200_000:
            raise ValueError('Bounded request required')
        kind = self.provider.adapter
        if reasoning != 'provider-default' and kind != 'openai_responses':
            raise ValueError('This adapter requires a separately qualified provider-specific reasoning configuration')
        if kind == 'openai_responses':
            payload = {'model':model, 'instructions':system, 'input':prompt,
                       'max_output_tokens':max_output_tokens, 'store':False}
            if reasoning != 'provider-default':
                payload['reasoning'] = {'effort':reasoning}
            data = self.request('POST', '/responses', payload)
            text = ''.join(c.get('text','') for item in data.get('output',[]) for c in item.get('content',[]) if c.get('type') == 'output_text')
            usage = data.get('usage') or {}
            return Generation(text, data.get('model'), data.get('id'), usage.get('input_tokens'),
                usage.get('output_tokens'), (usage.get('input_tokens_details') or {}).get('cached_tokens'), usage, data.get('status'))
        if kind == 'anthropic_messages':
            data = self.request('POST', '/messages', {'model':model,'system':system,
                'messages':[{'role':'user','content':prompt}],'max_tokens':max_output_tokens})
            usage = data.get('usage') or {}
            inputs = None if 'input_tokens' not in usage else sum(usage.get(k,0) for k in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens'))
            return Generation(''.join(c.get('text','') for c in data.get('content',[]) if c.get('type') == 'text'),
                data.get('model'), data.get('id'), inputs, usage.get('output_tokens'),
                usage.get('cache_read_input_tokens'), usage, data.get('stop_reason'))
        if kind == 'gemini':
            data = self.request('POST', f'/models/{quote(model,safe="-._")}:generateContent', {
                'systemInstruction':{'parts':[{'text':system}]},
                'contents':[{'role':'user','parts':[{'text':prompt}]}],
                'generationConfig':{'maxOutputTokens':max_output_tokens}})
            usage = data.get('usageMetadata') or {}
            candidates = data.get('candidates') or []
            candidate = candidates[0] if candidates else {}
            text = ''.join(p.get('text','') for p in candidate.get('content',{}).get('parts',[]) if not p.get('thought'))
            output = usage.get('candidatesTokenCount')
            if output is not None:
                output += usage.get('thoughtsTokenCount',0)
            return Generation(text, data.get('modelVersion'), data.get('responseId'), usage.get('promptTokenCount'),
                output, usage.get('cachedContentTokenCount'), usage, candidate.get('finishReason'))
        if kind == 'openai_compatible':
            data = self.request('POST', '/chat/completions', {'model':model,
                'messages':[{'role':'system','content':system},{'role':'user','content':prompt}],
                'max_tokens':max_output_tokens, 'stream':False})
            usage = data.get('usage') or {}
            choices = data.get('choices') or []
            choice = choices[0] if choices else {}
            return Generation(choice.get('message',{}).get('content') or '', data.get('model'), data.get('id'),
                usage.get('prompt_tokens'), usage.get('completion_tokens'),
                (usage.get('prompt_tokens_details') or {}).get('cached_tokens'), usage, choice.get('finish_reason'))
        raise ProviderError('unsupported_adapter')
