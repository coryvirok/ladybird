import http.server
import json
import os
import socketserver
import sys
import time
from urllib.parse import urlparse

# In-memory store for echo responses
echo_store = {}


class TestHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.static_directory, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_root_html().encode('utf-8'))
        elif self.path == '/shutdown':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Goodbye')
            self.server.server_close()
            print("Goodbye")
            sys.exit(0)
        elif self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'pong')
        elif self.path.startswith('/echo/'):
            self.handle_echo()
        elif self.path.startswith('/static/'):
            # Remove '/static/' prefix and use built-in method
            self.path = self.path[7:]
            return super().do_GET()
        else:
            self.send_error(404, 'Not Found')

    def do_POST(self):
        if self.path == '/create':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            response_def = json.loads(post_data.decode('utf-8'))

            response_id = str(len(echo_store) + 1)
            echo_store[response_id] = response_def

            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'id': response_id}).encode('utf-8'))
        elif self.path.startswith('/static/'):
            self.send_error(405, "Method Not Allowed")
        else:
            self.handle_echo()

    def do_OPTIONS(self):
        self.do_other()

    def do_PUT(self):
        self.do_other()

    def do_HEAD(self):
        self.do_other()

    def do_DELETE(self):
        self.do_other()

    def handle_echo(self):
        parsed_path = urlparse(self.path)
        response_id = parsed_path.path.split('/')[-1]

        if response_id in echo_store:
            response_def = echo_store[response_id]

            if 'delay' in response_def:
                time.sleep(response_def['delay'])

            # Send the status code without any default headers
            self.send_response_only(response_def.get('status_code', 200))

            # Set only the headers defined in the echo definition
            for header, value in response_def.get('headers', {}).items():
                self.send_header(header, value)
            self.end_headers()

            self.wfile.write(response_def.get('body', '').encode('utf-8'))
        else:
            self.send_error(404, 'Echo response not found')

    def do_other(self):
        if self.path.startswith('/echo/'):
            self.handle_echo()
        elif self.path.startswith('/static/'):
            self.send_error(405, "Method Not Allowed")
        else:
            self.send_error(404, 'Not Found')

    def get_root_html(self):
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTTP Test Server</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8">
    <div class="max-w-3xl mx-auto bg-white p-8 rounded-lg shadow-md">
        <h1 class="text-3xl font-bold mb-6 text-gray-800">HTTP Test Server</h1>

        <section class="mb-8">
            <h2 class="text-2xl font-semibold mb-4 text-gray-700">Available Endpoints:</h2>
            <ul class="list-disc pl-6 space-y-2 text-gray-600">
                <li><code class="bg-gray-200 px-2 py-1 rounded">/ping</code> - Simple health check (GET)</li>
                <li><code class="bg-gray-200 px-2 py-1 rounded">/create</code> - Create a new echo response (POST)</li>
                <li>
                    <code class="bg-gray-200 px-2 py-1 rounded">/echo/{{id}}</code>
                    - Get a specific echo response (GET, POST, PUT, OPTIONS, HEAD, DELETE)
                </li>
                <li><code class="bg-gray-200 px-2 py-1 rounded">/static/{{path}}</code> - Serve static files (GET)</li>
            </ul>
        </section>

        <section class="mb-8">
            <h2 class="text-2xl font-semibold mb-4 text-gray-700">Echo Definition Format:</h2>
            <pre class="bg-gray-100 p-4 rounded overflow-x-auto text-sm">
{{
    "status_code": int,
    "headers": {{
        "Header-Name": "Header-Value"
    }},
    "body": str,
    "delay": float  # Optional number of seconds
}}
            </pre>
        </section>

        <section class="mb-8">
            <h2 class="text-2xl font-semibold mb-4 text-gray-700">Example Usage (cURL):</h2>
            <p class="mb-2 text-gray-600">Create a new echo response:</p>
            <pre class="bg-gray-100 p-4 rounded overflow-x-auto text-sm mb-4">
curl -X POST http://localhost:{self.server.server_address[1]}/create -H "Content-Type: application/json" -d '{{
    "status_code": 200,
    "headers": {{
        "Content-Type": "application/json",
        "X-Custom-Header": "Custom Value"
    }},
    "body": "{{\\"message\\": \\"Hello, World!\\"}}",
    "delay": 1.5
}}'
            </pre>
            <p class="mb-2 text-gray-600">Access the created echo response:</p>
            <pre class="bg-gray-100 p-4 rounded overflow-x-auto text-sm">
curl http://localhost:{self.server.server_address[1]}/echo/1
            </pre>
        </section>

        <section class="mb-8">
            <h2 class="text-2xl font-semibold mb-4 text-gray-700">Example Usage (Browser JavaScript):</h2>
            <pre class="bg-gray-100 p-4 rounded overflow-x-auto text-sm mb-4">
// Create a new echo response
async function createEchoResponse() {{
    const response = await fetch('http://localhost:{self.server.server_address[1]}/create', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
        }},
        body: JSON.stringify({{
            status_code: 200,
            headers: {{
                'Content-Type': 'application/json',
                'X-Custom-Header': 'Custom Value'
            }},
            body: JSON.stringify({{ message: 'Hello from browser!' }}),
            delay: 1
        }}),
    }});
    const data = await response.json();
    console.log('Created echo response with ID:', data.id);
    return data.id;
}}

// Access the created echo response
async function accessEchoResponse(id) {{
    const response = await fetch(`http://localhost:{self.server.server_address[1]}/echo/${{id}}`);
    const data = await response.json();
    console.log('Received echo response:', data);
}}

// Usage
createEchoResponse().then(id => accessEchoResponse(id));
            </pre>
        </section>
    </div>
</body>
</html>
    """


def run_server(port=8000, static_directory="."):
    TestHTTPRequestHandler.static_directory = os.path.abspath(static_directory)
    with socketserver.TCPServer(("", port), TestHTTPRequestHandler) as httpd:
        print(f"Serving at http://localhost:{port}/")
        print(f"Serving static files from directory: {TestHTTPRequestHandler.static_directory}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run a test HTTP server')
    parser.add_argument('-p', '--port', type=int, default=8000, help='Port to run the server on')
    parser.add_argument('-d', '--directory', type=str, default=".", help='Directory to serve static files from')
    args = parser.parse_args()

    run_server(port=args.port, static_directory=args.directory)
