import uuid


def generate_tracking_number() -> str:
    return "TRK-" + str(uuid.uuid4().hex[:12]).upper()
