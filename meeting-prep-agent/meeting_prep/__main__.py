import os

from .api import make_server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    srv = make_server(os.environ.get("MPA_DB", "meeting_prep.db"), "0.0.0.0", port)
    print(f"Meeting Prep Agent API on :{port}  (set MPA_ADMIN_TOKEN to enable POST /users)")
    srv.serve_forever()
