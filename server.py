from flask import Flask, send_from_directory, abort
import os

# Create Flask app. The static_folder points to the project root so we can serve any file.
app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def root():
    """Serve the main index.html when accessing the root URL."""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    """Serve any existing file in the project directory.
    If the file does not exist a 404 is returned.
    """
    if os.path.isfile(filename):
        return send_from_directory('.', filename)
    else:
        abort(404)

if __name__ == '__main__':
    # Listen on all interfaces so the VPS can expose the service.
    app.run(host='0.0.0.0', port=8000)
