from pydantic import BaseModel
from typing import List, Optional


class DivisionBase(BaseModel):
    name: str


class DivisionCreate(DivisionBase):
    pass


class DivisionResponse(DivisionBase):
    id: int
    
    class Config:
        from_attributes = True


class DistrictBase(BaseModel):
    name: str
    division_id: int


class DistrictCreate(DistrictBase):
    pass


class DistrictResponse(DistrictBase):
    id: int
    division_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ThanaBase(BaseModel):
    name: str
    district_id: int


class ThanaCreate(ThanaBase):
    pass


class ThanaResponse(ThanaBase):
    id: int
    district_name: Optional[str] = None
    division_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class LocationHierarchy(BaseModel):
    divisions: List[DivisionResponse]
    districts: List[DistrictResponse]
    thanas: List[ThanaResponse]