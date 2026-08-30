from fastapi import APIRouter
from shared.contracts.idea import FounderInput
from shared.utils.ids import generate_venture_id

router = APIRouter()

@router.post("/ventures/start")
async def start_venture(input_data: FounderInput):
    venture_id = generate_venture_id()
    return {"venture_id": venture_id, "status": "INITIALIZED"}
