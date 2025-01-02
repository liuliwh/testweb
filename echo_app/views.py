import json
import logging
from collections import defaultdict
from functools import wraps

from flask import Response
from flask import render_template as orig_render_template
from flask import request
from werkzeug.routing import Rule

from . import app

logger = logging.getLogger(__name__)

# Template specfic handlers
_template_handler_registery = defaultdict(list)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/redirect/<times>/<code>/<anything>", methods=["post", "get"])
def do_redirect(times=0, code=302, anything=""):
    int_times = int(times)
    logger.warning(int_times)
    if int_times > 0:
        int_times -= 1
        return Response(
            None,
            status=code,
            headers={
                "Location": f"/redirect/{int_times}/{code}/{anything}",
            },
        )
    return render_template("home.html")


@app.route(
    "/return/<code>",
    defaults={"ctype": None, "anything": None},
    methods=["post", "get"],
)
@app.route(
    "/return/<code>/<ctype>",
    defaults={"anything": None},
    methods=["post", "get"],
)
@app.route(
    "/return/<code>/<ctype>/<anything>",
    methods=["post", "get"],
)
def do_return(code, ctype, anything):
    if ctype is None:
        return Response(None, status=code)
    if ctype == "html":
        return render_template("home.html", code)
    if ctype == "json":
        return Response(anything, status=code, content_type="application/json")
    raise NotImplementedError


@app.route("/dummy")
@app.route("/a/dummy")
@app.route("/a/dummy/dummy")
def dummy():
    return render_template("dummy.html")


@app.route("/websocketdemo")
def ws_demo():
    return render_template("ws_demo.html")


@app.route("/url/resource/")
def url_resource():
    return render_template("url_resource_hardcode.html")


@app.route("/anchor/")
def anchor():
    return render_template("anchor_hardcode.html")


@app.route("/gen_page", methods=["post", "get"])
def generate_page():
    """根据用户输入的json生成页面."""
    if request.method == "GET":
        return render_template("home.html")
    _content_encoding = request.content_encoding or "utf-8"
    data = request.data.decode(_content_encoding)
    if data.startswith("data=") and request.content_type == "text/plain":
        logger.info("handle generate page")
        return _generate_page(data)
    logger.info("生成的测试页面提交数据到/gen_page, echo only")
    return render_template("home.html")


@app.endpoint("catch_all")
def _404(_404):
    return render_template("home.html")


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template("home.html")


def _register_template_handler(template_name, func):
    """用于注册处理template非共用parameter的handler."""
    logger.info(f"Register template specific handlers:{template_name},{func.__name__}")
    _template_handler_registery[template_name].append(func)
    logger.info(_template_handler_registery)


def auto_register_tmpl_specific(template_names: str | list[str]):
    """A decorator 将func注册到_template_spec_handler中，即将template_name与func对应起来."""

    def decorate_auto_register(func):
        @wraps(func)
        def wrapper(data, *args, **kwargs):
            return func(data, *args, **kwargs)

        if isinstance(template_names, str):
            _register_template_handler(template_names, wrapper)
        elif isinstance(template_names, list):
            for t in template_names:
                _register_template_handler(t, wrapper)
        else:
            raise TypeError
        return wrapper

    return decorate_auto_register


def check_specific_in_data(func):
    """A decorator 检查data(函数的第一个参数)中是否有specific 属性.
    为简单起见，不使用inspect去查看func的singature，所以约定为function的首个参数名必须是data.
    在调用func的时候，当data dictionary不含有property 'specific'，则直接返回."""

    @wraps(func)
    def wrapper_validate(data, *args, **kwargs):
        if "specific" in data:
            return func(data, *args, **kwargs)

    return wrapper_validate


def _generate_page(data: str):
    """根据data提供的值,生成页面.
    前缀是data=,enc_type是plain"""
    # 自动化脚本用Python控制输入，会出现value:None的情况，替换成json:null
    logger.info(data)
    data = data.replace("None", "null")
    data = json.loads(data[len("data=") :])
    # 前端是stringfy的，所以这里要再次loads以转换为dict
    data = json.loads(data)
    logger.info(data)

    # Remove the None value,只管top level的
    data = {k: v for k, v in data.items() if v is not None}
    logger.info(f"after pop: {data}")

    template_name = data.get("template", "home")

    return render_template(template_name, data=data)


def render_template(template_name: str, status_code: int = 200, **context) -> Response:
    """根据data里面的信息，render template并且encode成对应的charset."""
    data = context.get("data", {})
    # 先处理公用的参数
    _common_template_params(data)
    # 模板特定的handler
    _template_name = template_name.split(".html", 1)[0]
    for handler in _template_handler_registery[_template_name]:
        handler(data)
    context["data"] = data

    data_str = orig_render_template(f"{_template_name}.html", **context)
    if data["charset"] == "utf-8":
        # Flask 默认用utf-8
        return data_str, status_code, {"Content-Type": data["response"]["content_type"]}
    try:
        encoded = data_str.encode(encoding=data["charset"])
    except UnicodeEncodeError as e:
        # 由于layout.html中有中文，当charset为Windows-1252的时候，在mac上可能会encode出错
        # 出错的时候，fallback成ignore error，这样子只是中文部分不显示
        # 手动render后再编码，作用是cover negative case的情况
        # 有机会在encode的时候ignore error
        logger.warning(e)
        encoded = data_str.encode(encoding=data["charset"], errors="ignore")
    return encoded, status_code, {"Content-Type": data["response"]["content_type"]}


def _common_template_params(data: dict) -> None:
    """从用户输入数据中，提取与构造render template时需要的数据.common section."""
    _set_ct(data)
    _set_base_tag(data)
    logger.info(f"common secion: {data}")


def _set_base_tag(data) -> None:
    """根据用户输入定义的base tag，处理并设值，以简化jinja template逻辑.
    规则: 如果原本未设置，就不再处理."""
    if "base_tag" not in data:
        return
    base_tag = data.get("base_tag")
    base_tag["tag_type"] = base_tag.get("tag_type", "static")
    base_tag["href"] = base_tag.get("href", "")


def _set_ct(data: dict) -> None:
    """根据用户输入的自定义response，set(mime,charset,content_type_str)"""
    custom_response = data.get("response", {})
    c_type = custom_response.get("content_type", "text/html; charset=utf-8")
    _, charset = c_type.split(";", 2)
    charset = charset.split("=")[1]

    # 将处理后的值置回data
    data["response"] = data.get("response", {})
    data["response"]["content_type"] = c_type
    # 将charset放在最上层，为了简化写jinja template
    data["charset"] = charset.strip().lower()


@app.context_processor
def inject_template_list():
    return {"template_list": app.config["TEMPLATE_LIST"]}


# ================================Template特定的处理=================
@auto_register_tmpl_specific("url_resource")
@check_specific_in_data
def url_resource_h(data: dict):
    """处理anchor template specific."""
    spec = data.get("specific")
    data["url"] = spec.get("url", "")
    data["url_type"] = spec.get("url_type", "static")


@auto_register_tmpl_specific("url_resource_hardcode")
def url_resource_hardcode_h(data: dict):
    """处理anchor template specific."""
    spec = data.get("specific", {})
    data["url_type"] = spec.get("url_type", "static")


@auto_register_tmpl_specific("url_resource_hardcode_tag")
def url_resource_hardcode_h_tag(data: dict):
    """处理anchor template specific."""
    spec = data.get("specific", {})
    data["url_type"] = spec.get("url_type", "static")


@auto_register_tmpl_specific("anchor")
@check_specific_in_data
def anchor_h(data: dict):
    """处理anchor template specific."""
    spec = data.get("specific")
    data["url"] = spec.get("url", "")
    data["url_type"] = spec.get("url_type", "static")
    if "url_download" in spec:
        data["url_download"] = spec.get("url_download")


@auto_register_tmpl_specific("tag_attri")
@check_specific_in_data
def tag_attri_h(data: dict):
    """处理anchor template specific."""
    spec = data.get("specific")
    data["url"] = spec.get("url", "")
    data["url_type"] = spec.get("url_type", "static")
    data["attri"] = spec.get("attri", "href")
    data["tag"] = spec.get("tag", "a")


@auto_register_tmpl_specific("tag_create")
@check_specific_in_data
def tag_create_h(data: dict):
    """处理anchor template specific."""
    spec = data.get("specific")
    data["url"] = spec.get("url", "")
    data["url_type"] = spec.get("url_type", "dynamic")
    data["attri"] = spec.get("attri", "href")
    data["tag"] = spec.get("tag", "a")


@auto_register_tmpl_specific("anchor_hardcode")
def anchor_hardcode_h(data: dict):
    """处理anchor template specific."""
    spec = data.get("specific", {})
    data["url_type"] = spec.get("url_type", "static")


@auto_register_tmpl_specific(["form"])
@check_specific_in_data
def form_h(data: dict):
    """处理form template specific."""
    spec = data.get("specific")
    data["url"] = spec.get("url", "")
    data["url_type"] = spec.get("url_type", "static")
    data["method"] = spec.get("method", "get")
    data["enc_type"] = spec.get("enc_type", "application/x-www-form-urlencoded")


@auto_register_tmpl_specific(["ajax"])
@check_specific_in_data
def ajax_h(data: dict):
    """处理ajax."""
    spec = data.get("specific")
    data["url"] = spec.get("url", "")
    data["url_type"] = spec.get("url_type", "static")
    data["method"] = spec.get("method", "get")
    data["withCredentials"] = str(spec.get("withCredentials", "")).lower()


@auto_register_tmpl_specific(["ajax_interval"])
@check_specific_in_data
def ajax_interval_h(data: dict):
    """处理ajax_interval."""
    spec = data.get("specific")
    data["url"] = spec.get("url", "/ajax_interval")
    data["url_type"] = spec.get("url_type", "static")
    data["method"] = spec.get("method", "get")
    data["withCredentials"] = str(spec.get("withCredentials", "")).lower()


# @auto_register_tmpl_specific("ajax_form")
# @check_specific_in_data
def ajax_flavor(data: dict):
    """处理ajax 相关的flavor"""
    spec = data.get("specific")
    data["flavor"] = spec.get("flavor", "vanilla")


app.url_map.add(Rule("/", defaults={"_404": ""}, endpoint="catch_all"))
app.url_map.add(Rule("/<path:_404>", endpoint="catch_all"))

logger.info(_template_handler_registery)
