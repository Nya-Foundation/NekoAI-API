from pydantic import BaseModel, ConfigDict, Field


class TextParams(BaseModel):
    """
    Generation parameters for the /ai/generate text endpoints.

    Only the commonly used sampling knobs are declared; any extra field is
    passed through to the API unchanged (`extra="allow"`), so the full set of
    parameters accepted by NovelAI (mirostat, cfg, logit_bias, ...) remains
    usable without library changes.

    Parameters
    ----------
    max_length: `int`, optional
        Maximum number of tokens to generate, defaults to 100
    min_length: `int`, optional
        Minimum number of tokens to generate, defaults to 1
    temperature: `float`, optional
        Sampling temperature, defaults to 1.0
    top_p: `float`, optional
        Nucleus sampling probability mass
    top_k: `int`, optional
        Top-k sampling cutoff
    repetition_penalty: `float`, optional
        Penalty applied to repeated tokens
    generate_until_sentence: `bool`, optional
        Keep generating until the end of a sentence, defaults to True
    """

    model_config = ConfigDict(extra="allow")

    # use_string makes the API accept and return plain text instead of token ids
    use_string: bool = True
    max_length: int = Field(default=100, ge=1, le=2048)
    min_length: int = Field(default=1, ge=1, le=2048)
    temperature: float = Field(default=1.0, ge=0.1, le=100)
    top_p: float | None = Field(default=None, ge=0, le=1)
    top_k: int | None = Field(default=None, ge=0)
    repetition_penalty: float | None = None
    generate_until_sentence: bool = True

    def to_payload(self) -> dict:
        return self.model_dump(exclude_none=True)
