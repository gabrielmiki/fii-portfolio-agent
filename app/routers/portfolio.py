from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from app.service import NotionSyncService
from app.db import get_db, User
from sqlalchemy.orm import Session

router = APIRouter()

def get_current_user_simple(
    x_user_email: str = Header(...), # Espera o cabeçalho "X-User-Email"
    session: Session = Depends(get_db)
) -> User:
    user = session.query(User).filter(User.email == x_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.post(
    "/sync/notion",
    summary="Inicia a sincronização do portfólio com o Notion em segundo plano",
    description="Dispara uma tarefa em segundo plano para sincronizar os ativos do portfólio com o Notion.",
    status_code=200
)
def trigger_notion_sync(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_simple),  # Assume user is obtained via some auth dependency
    session: Session = Depends(get_db),
):
    service = NotionSyncService(session, user)
    
    # O usuário recebe "Sync Started" imediatamente.
    # O Python continua rodando a função sync_portfolio em segundo plano.
    background_tasks.add_task(service.sync_portfolio)
    
    return {"message": "Sincronização com o Notion iniciada!"}