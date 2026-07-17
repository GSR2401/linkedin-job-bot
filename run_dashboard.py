"""
Run the Scraped Job Feed dashboard locally.
Serves the API and the static frontend on http://127.0.0.1:8000.
"""

import uvicorn

if __name__ == "__main__":
    print("Starting dashboard — open http://127.0.0.1:8000 in your browser.")
    uvicorn.run("app.server:app", host="127.0.0.1", port=8000)
