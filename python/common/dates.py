def pretty_time(s: int) -> str:
    """Converts seconds into human-readable time"""
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f'{h:d}h:{m:02d}m:{s:02d}s'
