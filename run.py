from app import create_app

# Thin entry point — all configuration lives in create_app().
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
