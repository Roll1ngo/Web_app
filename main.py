from http.server import HTTPServer, BaseHTTPRequestHandler
import pathlib
import urllib.parse
import mimetypes
import json
import socket
import logging
from threading import Thread
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


BASE_DIR = pathlib.Path()
# blog_path = BASE_DIR.joinpath(r"templates\blog.html")
env = Environment(loader=FileSystemLoader("templates"))
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
BUFFER = 1024


def send_data_to_socket(body):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(body, (SERVER_IP, SERVER_PORT))
    client_socket.close()


class MyHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html("index.html")
            case "/contact":
                self.send_html("message.html")
            case "/blog":
                self.render_template("blog.html")
            case _:
                static = BASE_DIR.joinpath(route.path[1:])
                if static.exists():
                    self.send_static(static)

                else:
                    self.send_html("error.html", 404)

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def send_static(self, filename):
        self.send_response(200)
        mime_type, *another = mimetypes.guess_type(filename)

        if mime_type:
            self.send_header("Content-Type", mime_type)
        else:
            self.send_header("Content-Type", "text/plain")

        self.end_headers()

        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        send_data_to_socket(body)

        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def render_template(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        with open("blog.json", "r", encoding="utf-8") as fd:
            r = json.load(fd)
        template = env.get_template(filename)
        print(template)
        html = template.render(blogs=r)
        self.wfile.write(html.encode())


def run(server=HTTPServer, handler=MyHTTPHandler):
    address = ("", 3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def save_date(data):
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = urllib.parse.unquote_plus(data.decode())

    try:
        split_body = [el.split("=") for el in body.split("&")]
        data_form = {current_date: {key: value for key, value in split_body}}

        storage_path = BASE_DIR.joinpath("storage/data.json")
        try:
            with open(storage_path, "r", encoding="utf-8") as fd_r:
                load_data = json.load(fd_r)
        except json.JSONDecodeError:
            load_data = {}

        data_form.update(load_data)

        with open(storage_path, "w", encoding="utf-8") as fd_w:
            json.dump(data_form, fd_w, ensure_ascii=False, indent=4)

    except ValueError as err:
        logging.error(f"Field parse data{body} with error: {err}")
    except OSError as err:
        logging.error(f"Field write data{body} with error: {err}")


def run_socker_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    server_socket.bind(server)

    try:
        while True:
            data, address = server_socket.recvfrom(BUFFER)
            save_date(data)
    except KeyboardInterrupt:
        logging.info("Socker server stoped")
    finally:
        server_socket.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    thread_server = Thread(target=run)
    thread_server.start()

    thread_socket = Thread(target=run_socker_server, args=(SERVER_IP, SERVER_PORT))
    thread_socket.start()
