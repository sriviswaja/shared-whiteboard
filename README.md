# shared-whiteboard
## Setup

    git clone https://github.com/sriviswaja/shared-whiteboard.git
    cd shared-whiteboard
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pytest
    uvicorn src.server.main:app --reload
