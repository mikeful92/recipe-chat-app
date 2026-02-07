import json
import time
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.recipe import Recipe, RecipeRequest


class OpenAIRecipeGenerator:
    _MAX_OUTPUT_TOKENS = 1200
    _REQUEST_TIMEOUT_SECONDS = 20.0
    _MAX_API_RETRIES = 2
    _BACKOFF_BASE_SECONDS = 0.25

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        if client is not None:
            self._client = client
            return

        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise RuntimeError("openai package is required for RECIPE_GENERATOR=openai") from exc

        self._client = OpenAI(api_key=api_key)

    @staticmethod
    def _to_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
        normalized = json.loads(json.dumps(schema))

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                properties = node.get("properties")
                if isinstance(properties, dict):
                    node["required"] = list(properties.keys())
                    node.setdefault("additionalProperties", False)
                    for value in properties.values():
                        _walk(value)

                items = node.get("items")
                if items is not None:
                    _walk(items)

                for key in ("anyOf", "allOf", "oneOf", "prefixItems"):
                    values = node.get(key)
                    if isinstance(values, list):
                        for value in values:
                            _walk(value)

                defs = node.get("$defs")
                if isinstance(defs, dict):
                    for value in defs.values():
                        _walk(value)

            elif isinstance(node, list):
                for value in node:
                    _walk(value)

        _walk(normalized)
        return normalized

    def generate(self, request: RecipeRequest) -> Recipe:
        validation_feedback: str | None = None

        for attempt in range(2):
            payload = self._generate_recipe_payload(request, validation_feedback)
            try:
                recipe = Recipe.model_validate(payload)
                recipe.id = str(uuid4())
                return recipe
            except ValidationError as exc:
                if attempt == 0:
                    validation_feedback = json.dumps(exc.errors(include_url=False))
                    continue
                raise RuntimeError("OpenAI response did not match Recipe schema") from exc

        raise RuntimeError("OpenAI generation failed")

    def _generate_recipe_payload(
        self, request: RecipeRequest, validation_feedback: str | None
    ) -> dict[str, Any]:
        prompt = (
            "Generate a recipe JSON object that strictly matches the provided JSON schema. "
            "Do not include extra keys. Keep ingredient and step ordering logical."
        )

        request_json = json.dumps(request.model_dump(), ensure_ascii=True)
        user_message = f"Input request: {request_json}"
        if validation_feedback:
            user_message += (
                "\nPrevious output failed validation. Fix all issues and regenerate. "
                f"Validation errors: {validation_feedback}"
            )

        request_kwargs = {
            "model": self._model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_message}]},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "recipe",
                    "strict": True,
                    "schema": self._to_strict_schema(Recipe.model_json_schema()),
                }
            },
            "max_output_tokens": self._MAX_OUTPUT_TOKENS,
            "timeout": self._REQUEST_TIMEOUT_SECONDS,
        }
        response = self._call_responses_with_retry(request_kwargs)

        output_text = self._extract_output_text(response)
        parsed = json.loads(output_text)
        if not isinstance(parsed, dict):
            raise RuntimeError("OpenAI response was not a JSON object")
        return parsed

    def _call_responses_with_retry(self, request_kwargs: dict[str, Any]) -> Any:
        for attempt in range(self._MAX_API_RETRIES + 1):
            try:
                return self._client.responses.create(**request_kwargs)
            except Exception as exc:
                if not self._is_retryable_api_error(exc) or attempt == self._MAX_API_RETRIES:
                    raise RuntimeError("OpenAI API request failed") from exc
                time.sleep(self._BACKOFF_BASE_SECONDS * (2**attempt))

        raise RuntimeError("OpenAI API request failed")

    @staticmethod
    def _is_retryable_api_error(exc: Exception) -> bool:
        retryable_error_names = {
            "APIConnectionError",
            "APITimeoutError",
            "RateLimitError",
            "InternalServerError",
        }
        if exc.__class__.__name__ in retryable_error_names:
            return True

        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code == 429 or status_code >= 500

        response = getattr(exc, "response", None)
        if response is not None:
            response_status_code = getattr(response, "status_code", None)
            if isinstance(response_status_code, int):
                return response_status_code == 429 or response_status_code >= 500

        return False

    @staticmethod
    def _extract_output_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text:
            return output_text

        if isinstance(response, dict):
            dict_output = response.get("output_text")
            if isinstance(dict_output, str) and dict_output:
                return dict_output

        raise RuntimeError("OpenAI response did not include output_text")
