from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field


def _blank_string_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _max_length_validator(max_length: int):
    def _validate(value: str | None) -> str | None:
        if value is not None and len(value) > max_length:
            raise ValueError(f"String should have at most {max_length} characters")
        return value

    return _validate


TrimmedNonEmptyStr = Annotated[str, Field(min_length=1)]


def TrimmedNonEmptyLimitedStr(max_length: int) -> type[str]:
    return Annotated[str, Field(min_length=1, max_length=max_length)]


def TrimmedOptionalLimitedStr(max_length: int) -> type[str | None]:
    return Annotated[
        str | None,
        BeforeValidator(_blank_string_to_none),
        AfterValidator(_max_length_validator(max_length)),
    ]


def TrimmedOptionalStr() -> type[str | None]:
    return Annotated[str | None, BeforeValidator(_blank_string_to_none)]


def TrimmedStringList(max_length: int) -> type[list[str]]:
    def _normalize(values: object) -> list[str]:
        if not isinstance(values, list):
            raise ValueError("Input should be a valid list")

        cleaned = [value.strip() for value in values if isinstance(value, str) and value.strip()]
        if not cleaned:
            raise ValueError("List must contain at least one non-empty value")
        return cleaned

    return Annotated[
        list[Annotated[str, Field(min_length=1, max_length=max_length)]],
        BeforeValidator(_normalize),
    ]
