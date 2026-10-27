from nexusserver import Application

app = Application()

@app.get("/")
def index(request):
    return "Hello, world!"

if __name__ == "__main__":
    app.run()