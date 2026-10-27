"""Hello world.

Run:  python -m nexusserver examples.hello_server:app --port 8080
"""

from nexusserver import Application

app = Application()


@app.get("/")
def index(request):
    return "Hello from NexusServer!"


if __name__ == "__main__":
    app.run()
