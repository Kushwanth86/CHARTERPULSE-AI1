from fastapi import APIRouter

from services.api.app.services.terminal_service import TerminalService


router = APIRouter(
    prefix="/api/v1/terminals",
    tags=["terminals"],
)

terminal_service = TerminalService()


@router.get("")
def list_terminals():
    terminals = terminal_service.list_terminals()

    return {
        "count": len(terminals),
        "data": terminals,
    }
