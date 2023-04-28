
"""
    news scrapper
"""

import uvicorn
# noinspection PyUnresolvedReferences
from src.main.main import app


if __name__ == "__main__":
    uvicorn.run('app:app', port=8080, env_file=".env.development", reload=True)
