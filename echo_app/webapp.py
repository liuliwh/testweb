# Entry point for the application.
import base64
import logging
import os
from typing import List

from flask import Response, request


# from . import middlewares
from . import app  # For application discovery by the 'flask' command.
from . import views  # For import side-effects of setting up routes.

logger = logging.getLogger(__name__)


def _template_name_list() -> List:
    """返回当前app的template name 列表,不包括layout.html,也不包括part_xxx.
    返回的列表不含html后缀."""
    filter_func = lambda x: x != "layout.html" and not x.startswith("part_")
    template_list = app.jinja_env.list_templates(filter_func=filter_func)
    return [x.removesuffix(".html") for x in template_list]


app.config["TEMPLATE_LIST"] = _template_name_list()

@app.template_filter("b64encode")
def b64encode_filter(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


@app.before_request
def handl_ajax():
    """针对ajax请求，全部优先echo."""
    logger.info(request.headers)
    is_ajax = request.headers.get("X-IS-AJAX", False)
    logger.info(f"is_ajax: {is_ajax}, {request.url}")
    # Patch 处理 alipay 文件上传
    is_alipay = request.user_agent.string.startswith("Alipay")
    is_upload = request.content_type and "multipart/form-data;" in request.content_type
    is_ajax = is_ajax or (is_alipay and is_upload)
    logger.info(f"is_ajax: {is_ajax}, {request.url}")
    if is_ajax:
        logger.info("Handle ajax")
        logger.info(request.headers)
        if request.content_type and "multipart/form-data;" in request.content_type:
            file = request.files["file"]
            file_name = file.name
            file_length = file.seek(0, os.SEEK_END)
            decoded = {"file_name": file_name, "file_length": file_length}
        elif request.content_length is None:
            decoded = request.get_data(as_text=True)
        elif request.content_length < 2048:
            decoded = request.get_data(as_text=True)
        else:
            decoded = "request data is too big"
        logger.info(decoded)
        data = {
            "url": request.url,
            "args": request.args,
            "data": decoded,
            "form": request.form,
        }
        return data, 200


@app.before_request
def dummy_resource_handler():
    """用于处理dummy的资源请求."""
    ext = (".ico", ".webm", ".mp4", ".jpg")
    mark = "_dummy_"
    resp = None
    dummy_ext = tuple([f"{mark}{t[1:]}" for t in ext])
    if request.path.endswith(ext):
        fname = os.path.basename(request.path)
        _, extension = fname.rsplit(".", 1)
        resp = app.send_static_file(f"dummy.{extension}")
    elif request.path.endswith(dummy_ext):
        start = request.path.rfind(mark)
        extension = request.path[start:]
        extension = extension.removeprefix(mark)
        resp = app.send_static_file(f"dummy.{extension}")
    elif request.path.endswith("/350x150"):
        resp = app.send_static_file("dummy.jpg")
    elif request.path.endswith(("_dummy.js", "_dummy_js")):
        resp = app.send_static_file("dummy.js")
    elif request.path.endswith("dummy.html"):
        resp = app.send_static_file("dummy.html")
    elif request.path.endswith("test.html"):
        resp = app.send_static_file("test.html")
    if resp:
        resp.headers["X-RAW-REQUEST"] = _encode_request_full_path()
        resp.headers["X-COOKIE-NAMES"] = _encode_cookie_in_request()
        return resp


@app.after_request
def change_header(resp: Response):
    """通过response header把收到的请求行以及cookie以base64编码后echo回去.
    为什么通过header去传递?因为有些response是资源文件类型如视频之类的，无法
    将请求行内容通过文本传过去。所以用header的方式传递，通用."""
    resp.headers["X-RAW-REQUEST"] = _encode_request_full_path()
    resp.headers["X-COOKIE-NAMES"] = _encode_cookie_in_request()
    resp.headers["X-SYS-INFO"] = request.headers.get("X-SYS-INFO")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def _encode_request_full_path() -> str:
    raw_request = request.url.removeprefix(f"{request.scheme}://{request.host}")
    return base64.b64encode(raw_request.encode("utf-8")).decode("utf-8")


def _encode_cookie_in_request() -> str:
    """将收到的请求的cookie name编码."""
    cookie_names = ";".join(k for k, _ in request.cookies.items())
    logger.info(f"rcved cookies: {cookie_names}")
    encoded = base64.b64encode(cookie_names.encode("utf-8"))
    return encoded.decode("utf-8")
