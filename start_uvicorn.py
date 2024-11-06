import uvicorn
import logging

# Configure logging
logging.basicConfig(filename='uvicorn_service.log', level=logging.INFO)

if __name__ == "__main__":
    try:
        uvicorn.run("IBH.asgi:application", host="0.0.0.0", port=8000, reload=False)
    except Exception as e:
        logging.error("Error starting Uvicorn: %s", e)
