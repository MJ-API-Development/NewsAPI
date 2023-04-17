
"""
    news scrapper
"""

import uvicorn
from src.main.main import app


if __name__ == "__main__":
    uvicorn.run('app:app', port=8000, env_file=".env.development", reload=True)