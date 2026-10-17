"""机器人规则、站点图与历史 URL 发现；不递归爬取发现的业务 URL。"""
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from hakrawler_process import run_process

MAX_DOCUMENT = 2 * 1024 * 1024
MAX_SITEMAPS = 16
MAX_URLS = 10000


class Scope:
    """仅接收 HTTP(S) URL，默认同主机，显式 -subs 才扩展子域。"""

    def __init__(self, url, subdomains=False):
        self.base = url
        self.host = urllib.parse.urlsplit(url).hostname
        self.subdomains = subdomains
        if not self.host or self.normalize(url) is None:
            raise ValueError("目标必须是无用户名密码的 HTTP(S) URL")

    def normalize(self, candidate):
        """归一化链接并检查范围；越界返回 None。"""
        try:
            url = urllib.parse.urlsplit(urllib.parse.urljoin(self.base, candidate))
            host = url.hostname
            if url.scheme not in ("http", "https") or not host or url.username or url.password:
                return None
            if host != self.host and not (self.subdomains and host.endswith("." + self.host)):
                return None
            return urllib.parse.urlunsplit(url._replace(fragment=""))
        except ValueError:
            return None


class ScopedRedirect(urllib.request.HTTPRedirectHandler):
    """在重定向请求发出前阻止越界，不在下载后才检查。"""

    def __init__(self, scope):
        self.scope = scope

    def redirect_request(self, request, fp, code, message, headers, newurl):
        """拒绝重定向到目标范围外的主机。"""
        if self.scope.normalize(newurl) is None:
            raise RuntimeError("补充资源重定向超出目标主机范围")
        return super().redirect_request(request, fp, code, message, headers, newurl)


class Fetcher:
    """复用用户的请求头、代理和 TLS 选项，限制下载字节与总耗时。"""

    def __init__(self, url, options, deadline):
        self.scope = Scope(url, options["subs"])
        self.options = options
        self.deadline = deadline
        self.headers = {"User-Agent": "Mozilla/5.0 (compatible; HexStrike-Hakrawler)"}
        for item in options["h"].split(";;"):
            if item:
                key, separator, value = item.partition(":")
                if not separator or not key.strip():
                    raise ValueError("-h 请求头必须使用 名称: 值 格式")
                self.headers[key.strip()] = value.strip()
        context = ssl._create_unverified_context() if options["insecure"] else ssl.create_default_context()
        proxies = {"http": options["proxy"], "https": options["proxy"]} if options["proxy"] else {}
        self.opener = urllib.request.build_opener(ScopedRedirect(self.scope),
            urllib.request.ProxyHandler(proxies), urllib.request.HTTPSHandler(context=context))

    def fetch(self, url, optional=False, probe=False):
        """获取范围内资源；只有可选文件的 404/410 被视为不存在。"""
        if self.scope.normalize(url) is None:
            raise ValueError("补充资源 URL 超出目标主机范围")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("补充资源下载达到总时间上限")
        request = urllib.request.Request(url, headers=self.headers)
        try:
            with self.opener.open(request, timeout=min(10, remaining)) as response:
                return b"" if probe else self._read(response)
        except urllib.error.HTTPError as error:
            if optional and error.code in (404, 410):
                return None
            raise RuntimeError(f"资源请求失败（HTTP {error.code}）：{url}") from error

    def _read(self, response):
        limit = MAX_DOCUMENT
        if self.options["size"] > 0:
            limit = min(limit, self.options["size"] * 1024)
        chunks, total = [], 0
        while True:
            if time.monotonic() >= self.deadline:
                raise TimeoutError("补充资源下载达到总时间上限")
            chunk = response.read(min(65536, limit + 1 - total))
            if not chunk:
                return b"".join(chunks)
            total += len(chunk)
            if total > limit:
                raise RuntimeError("补充资源大小超过下载上限")
            chunks.append(chunk)


def robots_entries(fetcher):
    """读取全部 User-agent 段的具体路径用于发现，不提交或访问这些路径。"""
    root = urllib.parse.urljoin(fetcher.scope.base, "/")
    data = optional_resource(fetcher, urllib.parse.urljoin(root, "robots.txt"))
    if data is None:
        return [], []
    if data.lstrip().startswith(b"<"):
        print("Hakrawler 补充来源不可用：robots.txt 返回了 HTML/XML 而非规则文本", file=sys.stderr)
        return [], []
    paths, maps = [], []
    for line in data.decode("utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("#")[0].partition(":")
        value = value.strip()
        if not separator or not value:
            continue
        key = key.strip().lower()
        url = fetcher.scope.normalize(urllib.parse.urljoin(root, value))
        if url and key == "sitemap":
            maps.append(url)
        elif url and key in ("allow", "disallow") and "*" not in value and "$" not in value:
            paths.append(url)
    return paths, maps


def sitemap_entries(fetcher, queue):
    """遍历有限数量的站点图索引；页面 loc 仅作为发现结果返回。"""
    visited = set()
    while queue:
        url = queue.pop(0)
        if url in visited or fetcher.scope.normalize(url) is None:
            continue
        if len(visited) >= MAX_SITEMAPS:
            raise RuntimeError("站点图数量超过 16 个上限，结果不完整")
        visited.add(url)
        data = optional_resource(fetcher, url)
        if data is None:
            continue
        tree = parse_sitemap(data, url)
        if tree is None:
            continue
        kind = tree.tag.rsplit("}", 1)[-1]
        for element in tree.iter():
            if element.tag.rsplit("}", 1)[-1] != "loc" or not element.text:
                continue
            link = fetcher.scope.normalize(element.text.strip())
            if link and kind == "sitemapindex":
                queue.append(link)
            elif link:
                yield "sitemap", link


def optional_resource(fetcher, url):
    """可选来源不可用时显示告警；不把主体爬取失败转成成功。"""
    try:
        return fetcher.fetch(url, optional=True)
    except (OSError, RuntimeError, ValueError) as error:
        if time.monotonic() >= fetcher.deadline:
            raise TimeoutError("补充资源下载达到总时间上限") from error
        print(f"Hakrawler 补充来源不可用：{url}（{error}）", file=sys.stderr)
        return None


class SitemapTreeBuilder(ET.TreeBuilder):
    """在 XML 解析阶段拒绝 DTD，覆盖 UTF-16 等非 ASCII 编码。"""

    def doctype(self, name, pubid, system):
        """拒绝站点图定义 DTD 或实体。"""
        raise ValueError("站点图不允许 DTD 或实体声明")


def parse_sitemap(data, url):
    """HTML 回退页或错误 XML 只令该补充来源不可用，不中止主体爬取。"""
    try:
        if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
            raise ValueError("站点图不允许 DTD 或实体声明")
        tree = ET.fromstring(data, parser=ET.XMLParser(target=SitemapTreeBuilder()))
        if tree.tag.rsplit("}", 1)[-1] not in ("urlset", "sitemapindex"):
            raise ValueError("站点图根节点必须为 urlset 或 sitemapindex")
        return tree
    except (ET.ParseError, ValueError) as error:
        print(f"Hakrawler 补充来源不可用：{url}（{error}）", file=sys.stderr)
        return None


def discover(fetcher, options):
    """补充来源只增加发现结果，不重新作为爬虫种子，避免绕过深度。"""
    maps = []
    if options["robots"]:
        paths, maps = robots_entries(fetcher)
        for url in paths:
            yield "robots", url
    if options["sitemap"]:
        root_map = urllib.parse.urljoin(fetcher.scope.base, "/sitemap.xml")
        yield from sitemap_entries(fetcher, [root_map] + maps)
    if options["wayback"]:
        environment = os.environ.copy()
        if options["proxy"]:
            environment.update(HTTP_PROXY=options["proxy"], HTTPS_PROXY=options["proxy"])
        output = run_process(["/usr/local/bin/waybackurls", "--no-subs", fetcher.scope.host],
                             "", fetcher.deadline, environment)
        for line in output.splitlines():
            url = fetcher.scope.normalize(line.strip())
            if url:
                yield "wayback", url
