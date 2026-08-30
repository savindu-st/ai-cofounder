import uuid

def generate_venture_id() -> str:
    return f"ven_{uuid.uuid4().hex[:12]}"
