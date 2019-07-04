#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/7/4 10:48 AM
# @Author  : w8ay
# @File    : command_system.py
import copy
import os
import re
from urllib.parse import urlparse

import requests

from lib.common import prepare_url
from lib.const import acceptedExt, ignoreParams
from lib.data import Share
from lib.output import out
from lib.plugins import PluginBase


class W13SCAN(PluginBase):
    name = '系统命令注入'
    desc = '''测试系统命令注入，支持Windows/Linux,暂只支持Get请求方式和回显型的命令注入'''

    def audit(self):
        method = self.requests.command  # 请求方式 GET or POST
        headers = self.requests.get_headers()  # 请求头 dict类型
        url = self.build_url()  # 请求完整URL
        data = self.requests.get_body_data().decode()  # POST 数据

        resp_data = self.response.get_body_data()  # 返回数据 byte类型
        resp_str = self.response.get_body_str()  # 返回数据 str类型 自动解码
        resp_headers = self.response.get_headers()  # 返回头 dict类型

        if method == 'GET':
            links = [url]
            for link in set(links):
                p = urlparse(link)
                if p.query == '':
                    continue
                exi = os.path.splitext(p.path)[1]
                if exi not in acceptedExt:
                    continue
                params = dict()
                for i in p.query.split("&"):
                    try:
                        key, value = i.split("=")
                        params[key] = value
                    except ValueError:
                        pass
                netloc = "{}://{}{}".format(p.scheme, p.netloc, p.path)

                url_flag = {
                    "set|set&set": [
                        'Path=[\s\S]*?PWD=',
                        'Path=[\s\S]*?PATHEXT=',
                        'Path=[\s\S]*?SHELL=)',
                        'Path\x3d[\s\S]*?PWD\x3d)',
                        'Path\x3d[\s\S]*?PATHEXT\x3d',
                        'Path\x3d[\s\S]*?SHELL\x3d',
                        'SERVER_SIGNATURE=[\s\S]*?SERVER_SOFTWARE=',
                        'SERVER_SIGNATURE\x3d[\s\S]*?SERVER_SOFTWARE\x3d',
                        'Non-authoritative\sanswer:\s+Name:\s*',
                        'Server:\s*.*?\nAddress:\s*'
                    ],
                }
                for k, v in params.items():
                    if k.lower() in ignoreParams:
                        continue
                    data = copy.deepcopy(params)
                    for spli in ['', ';']:
                        for flag, re_list in url_flag.items():
                            if spli == "":
                                data[k] = flag
                            else:
                                data[k] = v + flag
                            url1 = prepare_url(netloc, params=data)
                            if Share.in_url(url1):
                                continue
                            Share.add_url(url1)
                            r = requests.get(url1, headers=headers)
                            html1 = r.text
                            for rule in re_list:
                                if re.search(rule, html1, re.I | re.S | re.M):
                                    out.success(link, self.name, payload="{}:{}".format(k, data[k]))
                                    break
