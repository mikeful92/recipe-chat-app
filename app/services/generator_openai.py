import json
import logging
import time
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.recipe import Recipe, RecipeRequest

logger = logging.getLogger(__name__)

openai_generation_counters = {
    "success": 0,
    "failure": 0,
}


class OpenAIRecipeGenerationError(RuntimeError):
    def __init__(self, error_class: str, message: str, retry_count: int = 0) -> None:
        super().__init__(message)
        self.error_class = error_class
        self.retry_count = retry_count


class OpenAIRecipeGenerator:
    _MAX_OUTPUT_TOKENS = 1200
    _REQUEST_TIMEOUT_SECONDS = 20.0
    _MAX_API_RETRIES = 2
    _BACKOFF_BASE_SECONDS = 0.25

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        self._latest_api_retry_count = 0
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
            try:
                payload = self._generate_recipe_payload(request, validation_feedback)
                recipe = Recipe.model_validate(payload)
                recipe.id = str(uuid4())
                openai_generation_counters["success"] += 1
                logger.info(
                    "openai_recipe_generation",
                    extra={
                        "outcome": "success",
                        "generator_mode": "openai",
                        "retry_count": self._latest_api_retry_count,
                        **self._request_shape_fields(request),
                    },
                )
                return recipe
            except OpenAIRecipeGenerationError as exc:
                openai_generation_counters["failure"] += 1
                logger.warning(
                    "openai_recipe_generation",
                    extra={
                        "outcome": "failure",
                        "generator_mode": "openai",
                        "retry_count": exc.retry_count,
                        "error_class": exc.error_class,
                        **self._request_shape_fields(request),
                    },
                )
                raise
            except ValidationError as exc:
                if attempt == 0:
                    validation_feedback = json.dumps(exc.errors(include_url=False))
                    continue
                openai_generation_counters["failure"] += 1
                logger.warning(
                    "openai_recipe_generation",
                    extra={
                        "outcome": "failure",
                        "generator_mode": "openai",
                        "retry_count": self._latest_api_retry_count,
                        "error_class": "invalid_model_output",
                        **self._request_shape_fields(request),
                    },
                )
                raise OpenAIRecipeGenerationError(
                    "invalid_model_output",
                    "OpenAI response did not match Recipe schema",
                    retry_count=self._latest_api_retry_count,
                ) from exc

        raise OpenAIRecipeGenerationError("unknown", "OpenAI generation failed")

    def _generate_recipe_payload(
        self, request: RecipeRequest, validation_feedback: str | None
    ) -> dict[str, Any]:
        prompt = (
            "Generate a recipe JSON object that strictly matches the provided JSON schema. "
            "No extra keys. Keep ingredient and step order logical. "
            "Set dish_summary to a concise 1-3 sentence summary (max 320 chars)."
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
        response, retry_count = self._call_responses_with_retry(request_kwargs)
        self._latest_api_retry_count = retry_count

        output_text = self._extract_output_text(response)
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise OpenAIRecipeGenerationError(
                "invalid_model_output",
                "OpenAI response was not valid JSON",
                retry_count=retry_count,
            ) from exc
        if not isinstance(parsed, dict):
            raise OpenAIRecipeGenerationError(
                "invalid_model_output",
                "OpenAI response was not a JSON object",
                retry_count=retry_count,
            )
        return parsed

    def _call_responses_with_retry(self, request_kwargs: dict[str, Any]) -> tuple[Any, int]:
        for attempt in range(self._MAX_API_RETRIES + 1):
            try:
                return self._client.responses.create(**request_kwargs), attempt
            except Exception as exc:
                error_class, retryable = self._classify_api_error(exc)
                if not retryable or attempt == self._MAX_API_RETRIES:
                    raise OpenAIRecipeGenerationError(
                        error_class,
                        "OpenAI API request failed",
                        retry_count=attempt,
                    ) from exc
                time.sleep(self._BACKOFF_BASE_SECONDS * (2**attempt))

        raise OpenAIRecipeGenerationError("api_error", "OpenAI API request failed")

    @staticmethod
    def _classify_api_error(exc: Exception) -> tuple[str, bool]:
        error_name = exc.__class__.__name__
        if error_name == "APITimeoutError":
            return "timeout", True
        if error_name == "APIConnectionError":
            return "transport", True
        if error_name == "RateLimitError":
            return "rate_limit", True
        if error_name == "InternalServerError":
            return "server_error", True

        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            if status_code == 429:
                return "rate_limit", True
            if status_code >= 500:
                return "server_error", True
            return "api_error", False

        response = getattr(exc, "response", None)
        if response is not None:
            response_status_code = getattr(response, "status_code", None)
            if isinstance(response_status_code, int):
                if response_status_code == 429:
                    return "rate_limit", True
                if response_status_code >= 500:
                    return "server_error", True
                return "api_error", False

        return "api_error", False

    @staticmethod
    def _extract_output_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text:
            return output_text

        if isinstance(response, dict):
            dict_output = response.get("output_text")
            if isinstance(dict_output, str) and dict_output:
                return dict_output

        raise OpenAIRecipeGenerationError(
            "invalid_model_output", "OpenAI response did not include output_text"
        )

    @staticmethod
    def _request_shape_fields(request: RecipeRequest) -> dict[str, Any]:
        return {
            "has_theme": request.theme is not None,
            "ingredients_count": len(request.ingredients),
            "healthy": request.healthy,
            "quick_easy": request.quick_easy,
        }
