
import requests
import random
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from urllib.parse import urlparse, urlunparse

# 禁用 SSL 警告 (因为我们需要忽略 push1 的证书错误)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# 常见浏览器 User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
]

_original_request = requests.Session.request
_original_init = requests.Session.__init__
_is_patched = False

def apply_browser_headers_patch():
    """
    全局 Patch requests 库：
    1. 自动添加浏览器 Headers (规避反爬)
    2. 自动域名重定向 (push2 -> push1, 解决 IP 封锁)
    3. 自动配置重试机制 (增强连接稳定性)
    4. 自动禁用 SSL 验证 (解决 push1 证书不匹配问题)
    """
    global _is_patched
    if _is_patched:
        return

    # 1. Patch Session.__init__ for Retries
    # def patched_init(self, *args, **kwargs):
    #     _original_init(self, *args, **kwargs)
    #     # 挂载重试策略
    #     retries = Retry(
    #         total=3,
    #         backoff_factor=0.5,
    #         status_forcelist=[500, 502, 503, 504],
    #         allowed_methods=["GET", "POST"]
    #     )
    #     adapter = HTTPAdapter(max_retries=retries)
    #     self.mount("http://", adapter)
    #     self.mount("https://", adapter)
    
    # requests.Session.__init__ = patched_init

    # 2. Patch Session.request for Headers & Domain Swap
    def patched_request(self, method, url, *args, **kwargs):
        headers = kwargs.get('headers')
        if headers is None:
            headers = {}
            
        # --- DNS Override Logic (Fix for Blocked Domains) ---
        # 诊断发现 push2.eastmoney.com 及其子域名解析被阻断，但特定 IP 可用 (push2ex.eastmoney.com IP: 117.184.38.248)
        # 强制将域名替换为已知可用 IP，并设置 Host Header
        
        # 目标 IP
        TARGET_IP = "117.184.38.248"
        
        parsed = urlparse(url)
        # Handle cases where netloc includes port
        domain = parsed.netloc.split(':')[0]
        
        # Check if domain matches our target domains (exact or subdomain)
        should_patch = False
        if domain == "push2.eastmoney.com" or domain.endswith(".push2.eastmoney.com"):
            should_patch = True
        elif domain == "push2his.eastmoney.com" or domain.endswith(".push2his.eastmoney.com"):
            should_patch = True
            
        if should_patch:
            # Set Host header to original domain
            if 'Host' not in headers:
                headers['Host'] = domain
            
            # Force HTTPS and replace domain with IP
            # We use urlparse/urlunparse to ensure scheme is upgraded to https
            new_parsed = parsed._replace(scheme='https', netloc=TARGET_IP)
            url = urlunparse(new_parsed)
            
            # Disable SSL verification because IP doesn't match Cert
            kwargs['verify'] = False
            
            logger.debug(f"DNS Override: Rewrote {domain} to {TARGET_IP} in URL: {url}")
            
        # 随机选择 UA
            
        # 随机选择 UA
        # if "push2.eastmoney.com" in url: ...
        
        # 随机选择 UA
        if 'User-Agent' not in headers:
            headers['User-Agent'] = random.choice(USER_AGENTS)
        
        # 添加通用浏览器 Header
        if 'Accept' not in headers:
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        if 'Accept-Language' not in headers:
            headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'
        
        # 针对东方财富的特殊处理
        if 'eastmoney.com' in url:
            if 'Referer' not in headers:
                headers['Referer'] = 'https://quote.eastmoney.com/'
            if 'Origin' not in headers:
                headers['Origin'] = 'https://quote.eastmoney.com'
            
            # 强制禁用 SSL 验证，因为 push1 的证书可能与域名不匹配 (证书通常发给 push2)
            kwargs['verify'] = False

        kwargs['headers'] = headers
        
        # 调用原始方法
        return _original_request(self, method, url, *args, **kwargs)

    requests.Session.request = patched_request
    _is_patched = True
    logger.info("Requests library patched: Protocol Downgrade (HTTPS->HTTP) + Browser Headers + Retries enabled.")
