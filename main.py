# ─── ServerListDB ─────────────────────────────────────────────
class ServerListDB:
    PATH = "SERVER/server_list.db"

    def __init__(self):
        self.c = sqlite3.connect(self.PATH, check_same_thread=False)
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.executescript("""
            CREATE TABLE IF NOT EXISTS servers(
                guild_id TEXT PRIMARY KEY, 
                guild_name TEXT,
                status TEXT NOT NULL DEFAULT 'invited',
                joined_at TEXT, 
                expires_at TEXT, 
                license_key TEXT);
        """)
        self.c.commit()

    def upsert(self, guild_id: int, name: str, status="invited", expires_at=None, license_key=None):
        """서버 정보 등록/업데이트"""
        self.c.execute("""
            INSERT INTO servers(guild_id, guild_name, status, joined_at, expires_at, license_key)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                guild_name = excluded.guild_name,
                status = excluded.status,
                expires_at = COALESCE(excluded.expires_at, expires_at),
                license_key = COALESCE(excluded.license_key, license_key)
        """, (str(guild_id), name, status, _iso(_now()), expires_at, license_key))
        self.c.commit()

    def delete(self, guild_id: int) -> Optional[dict]:
        """서버 완전 삭제 (가장 중요)"""
        gid_str = str(guild_id)
        
        # 삭제 전 데이터 백업용으로 반환
        row = self.c.execute("SELECT * FROM servers WHERE guild_id=?", (gid_str,)).fetchone()
        if not row:
            return None
            
        data = dict(zip(_cols(self.c, "servers"), row))

        # 실제 삭제
        self.c.execute("DELETE FROM servers WHERE guild_id=?", (gid_str,))
        self.c.commit()
        
        return data

    def get_all(self, status=None) -> list[dict]:
        if status:
            rows = self.c.execute(
                "SELECT * FROM servers WHERE status=? ORDER BY joined_at DESC", 
                (status,)
            ).fetchall()
        else:
            rows = self.c.execute(
                "SELECT * FROM servers ORDER BY joined_at DESC"
            ).fetchall()
        return _rows(self.c, "servers", rows)

    def set_expired(self, guild_id: int):
        """만료 처리"""
        self.c.execute(
            "UPDATE servers SET status='expired' WHERE guild_id=?", 
            (str(guild_id),)
        )
        self.c.commit()

    def get_by_guild(self, guild_id: int) -> Optional[dict]:
        """특정 서버 정보 조회"""
        row = self.c.execute(
            "SELECT * FROM servers WHERE guild_id=?", 
            (str(guild_id),)
        ).fetchone()
        return dict(zip(_cols(self.c, "servers"), row)) if row else None
