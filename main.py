def is_registered(guild_id: int) -> bool:
    """서버가 활성 등록 상태인지 확인"""
    from utils.db import ServerListDB
    try:
        sldb = ServerListDB()
        row = sldb.c.execute(
            "SELECT 1 FROM servers WHERE guild_id=? AND status='active'", 
            (str(guild_id),)
        ).fetchone()
        return row is not None
    except:
        return False
