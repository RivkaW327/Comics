import uvicorn
from .main import app
from .config.config_loader import config
import logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    uvicorn.run("FastAPIProject.main:app", host=config["server"]["host"], port=config["server"]["port"])#, reload=True)
