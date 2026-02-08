import json

import pytest

from app.schemas.recipe import RecipeRequest
from app.services.generator_openai import (
    OpenAIRecipeGenerationError,
    OpenAIRecipeGenerator,
    openai_generation_counters,
)


class APIConnectionError(Exception):
    pass


class APITimeoutError(Exception):
    pass


class FakeResponses:
    def __init__(self, sequence: list[dict | str | Exception | object]) -> None:
        self._sequence = sequence
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self._sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        if not isinstance(item, (dict, str)):
            return item

        class Response:
            output_text = item if isinstance(item, str) else json.dumps(item)

        return Response()


class FakeOpenAIClient:
    def __init__(self, sequence: list[dict | str | Exception | object]) -> None:
        self.responses = FakeResponses(sequence)


class ResponseWithoutOutputText:
    pass


def _valid_recipe_payload() -> dict:
    return {
        "id": "model-provided-id",
        "title": "Tomato Basil Pasta",
        "servings": 2,
        "time_minutes": 20,
        "difficulty": "easy",
        "ingredients": [
            {"name": "tomato", "amount": "2", "unit": "item", "optional": False},
            {"name": "basil", "amount": "5", "unit": "leaf", "optional": False},
        ],
        "steps": [
            {"step": 1, "text": "Chop tomatoes.", "timer_minutes": None},
            {"step": 2, "text": "Mix with basil.", "timer_minutes": None},
        ],
        "substitutions": ["Use parsley instead of basil."],
        "cook_mode": {
            "ingredients_checklist": ["Gather tomatoes", "Gather basil"],
            "step_cards": ["Chop tomatoes.", "Mix with basil."],
        },
    }


def test_openai_generator_returns_valid_recipe_and_overrides_id() -> None:
    client = FakeOpenAIClient([_valid_recipe_payload()])
    generator = OpenAIRecipeGenerator(api_key="test-key", model="gpt-4.1-mini", client=client)

    recipe = generator.generate(RecipeRequest(ingredients=["tomato", "basil"]))

    assert recipe.title == "Tomato Basil Pasta"
    assert recipe.id != "model-provided-id"
    assert len(client.responses.calls) == 1
    sent_schema = client.responses.calls[0]["text"]["format"]["schema"]
    ingredient_schema = sent_schema["$defs"]["RecipeIngredient"]
    assert "optional" in ingredient_schema["required"]
    assert client.responses.calls[0]["max_output_tokens"] == 1200
    assert client.responses.calls[0]["timeout"] == 20.0


def test_openai_generator_retries_once_on_validation_failure() -> None:
    invalid = _valid_recipe_payload()
    invalid.pop("steps")
    valid = _valid_recipe_payload()
    client = FakeOpenAIClient([invalid, valid])
    generator = OpenAIRecipeGenerator(api_key="test-key", model="gpt-4.1-mini", client=client)

    recipe = generator.generate(RecipeRequest(theme="Italian"))

    assert recipe.title == "Tomato Basil Pasta"
    assert len(client.responses.calls) == 2


def test_openai_generator_retries_on_transport_error_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr("app.services.generator_openai.time.sleep", lambda _: None)
    client = FakeOpenAIClient([APIConnectionError("timeout"), _valid_recipe_payload()])
    generator = OpenAIRecipeGenerator(api_key="test-key", model="gpt-4.1-mini", client=client)

    recipe = generator.generate(RecipeRequest(theme="Italian"))

    assert recipe.title == "Tomato Basil Pasta"
    assert len(client.responses.calls) == 2


def test_openai_generator_retries_on_timeout_error_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr("app.services.generator_openai.time.sleep", lambda _: None)
    client = FakeOpenAIClient([APITimeoutError("timeout"), _valid_recipe_payload()])
    generator = OpenAIRecipeGenerator(api_key="test-key", model="gpt-4.1-mini", client=client)

    recipe = generator.generate(RecipeRequest(theme="Italian"))

    assert recipe.title == "Tomato Basil Pasta"
    assert len(client.responses.calls) == 2


def test_openai_generator_raises_when_transport_retries_exhausted(monkeypatch) -> None:
    monkeypatch.setattr("app.services.generator_openai.time.sleep", lambda _: None)
    client = FakeOpenAIClient(
        [APIConnectionError("1"), APIConnectionError("2"), APIConnectionError("3")]
    )
    generator = OpenAIRecipeGenerator(api_key="test-key", model="gpt-4.1-mini", client=client)

    with pytest.raises(OpenAIRecipeGenerationError, match="OpenAI API request failed"):
        generator.generate(RecipeRequest(theme="Italian"))

    assert len(client.responses.calls) == 3


def test_openai_generator_raises_when_output_text_missing() -> None:
    client = FakeOpenAIClient([ResponseWithoutOutputText()])
    generator = OpenAIRecipeGenerator(api_key="test-key", model="gpt-4.1-mini", client=client)

    with pytest.raises(OpenAIRecipeGenerationError, match="did not include output_text"):
        generator.generate(RecipeRequest(theme="Italian"))


def test_openai_generator_raises_when_output_is_non_json() -> None:
    client = FakeOpenAIClient(["not-json"])
    generator = OpenAIRecipeGenerator(api_key="test-key", model="gpt-4.1-mini", client=client)

    with pytest.raises(OpenAIRecipeGenerationError, match="not valid JSON"):
        generator.generate(RecipeRequest(theme="Italian"))


def test_openai_generator_safe_structured_logs_and_no_secrets(monkeypatch, caplog) -> None:
    monkeypatch.setattr("app.services.generator_openai.time.sleep", lambda _: None)
    openai_generation_counters["success"] = 0
    openai_generation_counters["failure"] = 0
    client = FakeOpenAIClient([APIConnectionError("timeout"), _valid_recipe_payload()])
    generator = OpenAIRecipeGenerator(api_key="super-secret-key", model="gpt-4.1-mini", client=client)

    with caplog.at_level("INFO", logger="app.services.generator_openai"):
        generator.generate(RecipeRequest(theme="Italian", ingredients=["tomato"]))

    records = [r for r in caplog.records if r.msg == "openai_recipe_generation"]
    assert records
    success = records[-1]
    assert success.outcome == "success"
    assert success.generator_mode == "openai"
    assert success.retry_count == 1
    assert hasattr(success, "has_theme")
    assert hasattr(success, "ingredients_count")
    assert hasattr(success, "healthy")
    assert hasattr(success, "quick_easy")
    assert openai_generation_counters["success"] == 1
    assert openai_generation_counters["failure"] == 0
    assert "super-secret-key" not in caplog.text
    assert "Input request:" not in caplog.text
    assert "Tomato Basil Pasta" not in caplog.text
