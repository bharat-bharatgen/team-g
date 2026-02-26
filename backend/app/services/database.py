from app.dependencies import get_database

class DatabaseService:
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        self.db = await get_database()

