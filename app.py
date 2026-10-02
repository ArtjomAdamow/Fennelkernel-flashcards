from flashcards_app import callbacks  # noqa: F401  side-effect import registers the Dash callback
from flashcards_app.server import app, main

if __name__ == "__main__":
    main()
