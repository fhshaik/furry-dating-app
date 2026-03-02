from pydantic import BaseModel


class SpeciesTagResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}
