from app.db.session import get_db
from app.services.docker_service import DockerService

def get_docker_service() -> DockerService:
    return DockerService()
