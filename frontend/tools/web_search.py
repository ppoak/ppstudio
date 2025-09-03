"""
title: Web Search
author: ppoak
version: 0.0.3
author: ppoak
author_url: https://github.com/ppoak
description: A powerful search tool
"""

import re
import json
import math
import urllib
import random
import execjs
import serpapi
import requests
from ddgs import DDGS
from datetime import datetime
from pydantic import BaseModel, Field


class Tools:

    class UserValves(BaseModel):
        xhs_api_key: str = Field(
            default="",
            description="The cookie string extracted from logged https://www.xiaohongshu.com",
        )
        serp_api_key: str = Field(
            default="",
            description="The api key shown on logged https://serpapi.com/dashboard",
        )

    async def general_search(
        self, query: str, num: int = 10, __user__=None, __event_emitter__=None
    ):
        """
        General search the query without extending any web page, only snippets
        :param query str: The query string from user
        :num int: The number of items in the scraped result, default to 10
        :return: The scraped result
        """
        try:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Searching with DDGS ...",
                        "done": False,
                        "hidden": False,
                    },
                }
            )
            serp_api_key = __user__["valves"].serp_api_key
            content = f"# Search Results of {query}"
            try:
                results = DDGS().text(
                    query, region="cn-zh", max_results=num // 2 if serp_api_key else num
                )
                for result in results:
                    content += f"\n\n## {result['title']}\n\n{result['body']}"
            except:
                content += "\n\nDDGS is not available currently."
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Searching with Serpapi ...",
                        "done": False,
                        "hidden": False,
                    },
                }
            )
            if serp_api_key:
                client = serpapi.Client(api_key=serp_api_key)
                results = dict(
                    client.search(
                        {
                            "engine": "google",
                            "q": query,
                            "google_domain": "google.com",
                            "device": "desktop",
                            "num": str(num // 2),
                        }
                    )
                )
                for result in results["organic_results"]:
                    content += f"\n\n## {result['title']}\n\n{result.get('snippet', 'Snippet Not Available')}"
                    if result.get("sitelinks", None):
                        for sitelink in result["sitelinks"].get("expanded", []):
                            content += f"\n\n### {sitelink['title']}\n\n{result['link']}\n\n{result.get('snippet', 'Snippet Not Available')}"
                content += f"\n\n## Knowledge Graph about {query}\n\n```json\n{results.get('knowledge_graph', 'Not Available')}\n```"

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Finished searching ...",
                        "done": True,
                        "hidden": False,
                    },
                }
            )
            return content

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Error: {str(e)} ...",
                        "done": True,
                        "hidden": False,
                    },
                }
            )
            return str(e)

    def read_content(self, url: str, __event_emitter__=None) -> str:
        """
        Read full content of a website.

        :param url str: The URL of the web page to scrape.
        :return: The scraped and processed markdown content without the Links/Buttons section, or an error message.
        """
        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            "X-No-Cache": "true",
            "X-With-Images-Summary": "true",
            "X-With-Links-Summary": "true",
        }

        try:
            response = requests.get(jina_url, headers=headers)
            response.raise_for_status()
            return response.text

        except Exception as e:
            return f"Error when read content: {str(e)}"

    async def deep_search(
        self, query: str, num: int = 3, __user__=None, __event_emitter__=None
    ):
        """
        Deep search the query extending every webpage in result
        :param query str: The query string from user
        :num int: The number of items in the scraped result, default to "10"
        :return: The scraped result
        """
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Searching Reference ...",
                    "done": False,
                    "hidden": False,
                },
            }
        )
        serp_api_key = __user__["valves"].serp_api_key
        try:
            try:
                results = DDGS().text(
                    query, region="cn-zh", max_results=num // 2 if serp_api_key else num
                )
            except:
                results = []
            if serp_api_key:
                client = serpapi.Client(api_key=serp_api_key)
                serp_results = dict(
                    client.search(
                        {
                            "engine": "google",
                            "q": query,
                            "google_domain": "google.com",
                            "device": "desktop",
                            "num": str(num // 2),
                        }
                    )
                )
                results += [
                    {"title": org_res["title"], "href": org_res["link"]}
                    for org_res in serp_results["organic_results"]
                ]
            content = f"# Search Results of {query}"
            for i, result in enumerate(results, start=1):
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Downloading Full Page {i} / {len(results)} ...",
                            "done": False,
                            "hidden": False,
                        },
                    }
                )
                link = result["href"]
                page_content = self.read_content(link)
                content += (
                    f"\n\n## {result['title']}\n\n{page_content}"
                )
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Finished Deep Search",
                        "done": True,
                        "hidden": False,
                    },
                }
            )
            return content
        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Error when deep search: {e}",
                        "done": True,
                        "hidden": False,
                    },
                }
            )
            return str(e)

    def get_xhs_note(self, url: list, __user__=None):
        """Get the content of one or some specified xiaohongshu(小红书) note urls
        :param url list: The url list of the xiaohongshu(小红书) note
        :return: The xiaohongshu(小红书) note result in markdown format
        """
        datas = []
        cookie = __user__["valves"].xhs_api_key
        for u in url:
            datas.append(
                XHS_Apis().get_note_info(
                    u,
                    cookies_str=cookie,
                )
            )
        content = ""
        for success, message, data in datas:
            if success:
                data = data["data"]["items"][0]["note_card"]
                content += (
                    f"## {data['title']}\n\n{data['desc']}\n\n"
                    + "\n".join(
                        [
                            f"- ![Reference Image]({image['url_default']})"
                            for image in data["image_list"]
                        ]
                    )
                    + "\n\n"
                    + "\t".join([f"#{tag['name']}" for tag in data["tag_list"]])
                    + "\n\n"
                    + f"Liked: {data['interact_info']['liked_count']}\tCollected: {data['interact_info']['collected_count']}\tComment: {data['interact_info']['comment_count']}\tShare: {data['interact_info']['share_count']}\n\n"
                    + f"Created by [{data['user']['nickname']}](https://www.xiaohongshu.com/user/profile/{data['user']['user_id']}) at {data.get('ip_location', '未知')}, Uploaded at {datetime.fromtimestamp(data['time'] / 1e3)}, Updated at {datetime.fromtimestamp(data['last_update_time'] / 1e3)}\n\n"
                )
            else:
                content += f"## {message}"
        return content

    async def search_xhs_note(
        self,
        query: str,
        num: int = 10,
        sort_type_choice: int = 0,
        note_type: int = 0,
        note_time: int = 0,
        note_range: int = 0,
        pos_distance: int = 0,
        geo: dict = "",
        __user__=None,
        __event_emitter__=None,
    ):
        """Get the aggragated result of the specified query string from xiaohongshu(小红书)
        :param query str: The query string to search on xiaohongshu(小红书)
        :param num int: The number of result from xiaohongshu(小红书) to aggregate, default to 10
        :param sort_type_choice Sorting method 0 Comprehensive sort, 1 Latest, 2 Most likes, 3 Most comments, 4 Most favorites
        :param note_type Note type 0 No limit, 1 Video notes, 2 Regular notes
        :param note_time Note time 0 No limit, 1 Within one day, 2 Within one week, 3 Within six months
        :param note_range Note range 0 No limit, 1 Viewed, 2 Unviewed, 3 Followed
        :param pos_distance Position distance 0 No limit, 1 Same city, 2 Nearby This must be specified with geo
        :param geo: Location information latitude and longitude
        :return: The aggregated result
        """
        cookie = __user__["valves"].xhs_api_key
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Searching General Result ...",
                    "done": False,
                    "hidden": False,
                },
            }
        )
        success, message, notes = XHS_Apis().search_some_note(
            query,
            num,
            cookie,
            sort_type_choice,
            note_type,
            note_time,
            note_range,
            pos_distance,
            geo,
        )
        note_list = []
        content = "# XHS Aggregated Search Result\n\n"
        if success:
            notes = list(filter(lambda x: x["model_type"] == "note", notes))
            for note in notes:
                note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                note_list.append(note_url)
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Getting Note Detail ...",
                        "done": False,
                        "hidden": False,
                    },
                }
            )
            content += self.get_xhs_note(note_list, __user__=__user__)
        else:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Failed Getting General Result ...",
                        "done": False,
                        "hidden": False,
                    },
                }
            )
            content += message
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Finished Gathering Message",
                    "done": True,
                    "hidden": False,
                },
            }
        )
        return content


class XHS_Apis:
    def __init__(self):
        self.base_url = "https://edith.xiaohongshu.com"
        self.js = execjs.compile(
            open(r"tools/static/xhs_xs_xsc_56.js", "r", encoding="utf-8").read()
        )
        self.xray_js = execjs.compile(
            open(r"tools/static/xhs_xray.js", "r", encoding="utf-8").read()
        )

    def generate_x_b3_traceid(self, len=16):
        x_b3_traceid = ""
        for t in range(len):
            x_b3_traceid += "abcdef0123456789"[math.floor(16 * random.random())]
        return x_b3_traceid

    def generate_xs_xs_common(self, a1, api, data=""):
        ret = self.js.call("get_request_headers_params", api, data, a1)
        xs, xt, xs_common = ret["xs"], ret["xt"], ret["xs_common"]
        return xs, xt, xs_common

    def generate_xs(self, a1, api, data=""):
        ret = self.js.call("get_xs", api, data, a1)
        xs, xt = ret["X-s"], ret["X-t"]
        return xs, xt

    def generate_xray_traceid(self):
        return self.xray_js.call("traceId")

    def get_common_headers(self):
        return {
            "authority": "www.xiaohongshu.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://www.xiaohongshu.com/",
            "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }

    def get_request_headers_template(self):
        return {
            "authority": "edith.xiaohongshu.com",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "cache-control": "no-cache",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://www.xiaohongshu.com",
            "pragma": "no-cache",
            "referer": "https://www.xiaohongshu.com/",
            "sec-ch-ua": '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "x-b3-traceid": "",
            "x-mns": "unload",
            "x-s": "",
            "x-s-common": "",
            "x-t": "",
            "x-xray-traceid": self.generate_xray_traceid(),
        }

    def generate_headers(self, a1, api, data=""):
        xs, xt, xs_common = self.generate_xs_xs_common(a1, api, data)
        x_b3_traceid = self.generate_x_b3_traceid()
        headers = self.get_request_headers_template()
        headers["x-s"] = xs
        headers["x-t"] = str(xt)
        headers["x-s-common"] = xs_common
        headers["x-b3-traceid"] = x_b3_traceid
        if data:
            data = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return headers, data

    def generate_request_params(self, cookies_str, api, data=""):
        cookies = self.trans_cookies(cookies_str)
        a1 = cookies["a1"]
        headers, data = self.generate_headers(a1, api, data)
        return headers, cookies, data

    def splice_str(self, api, params):
        url = api + "?"
        for key, value in params.items():
            if value is None:
                value = ""
            url += key + "=" + value + "&"
        return url[:-1]

    def trans_cookies(self, cookies_str):
        if "; " in cookies_str:
            ck = {
                i.split("=")[0]: "=".join(i.split("=")[1:])
                for i in cookies_str.split("; ")
            }
        else:
            ck = {
                i.split("=")[0]: "=".join(i.split("=")[1:])
                for i in cookies_str.split(";")
            }
        return ck

    def get_homefeed_all_channel(self, cookies_str: str, proxies: dict = None):
        res_json = None
        try:
            api = "/api/sns/web/v1/homefeed/category"
            headers, cookies, data = self.generate_request_params(cookies_str, api)
            response = requests.get(
                self.base_url + api, headers=headers, cookies=cookies, proxies=proxies
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_homefeed_recommend(
        self,
        category,
        cursor_score,
        refresh_type,
        note_index,
        cookies_str: str,
        proxies: dict = None,
    ):
        """
        获取主页推荐的笔记
        :param category: 你想要获取的频道
        :param cursor_score: 你想要获取的笔记的cursor
        :param refresh_type: 你想要获取的笔记的刷新类型
        :param note_index: 你想要获取的笔记的index
        :param cookies_str: 你的cookies
        返回主页推荐的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/homefeed"
            data = {
                "cursor_score": cursor_score,
                "num": 20,
                "refresh_type": refresh_type,
                "note_index": note_index,
                "unread_begin_note_id": "",
                "unread_end_note_id": "",
                "unread_note_count": 0,
                "category": category,
                "search_key": "",
                "need_num": 10,
                "image_formats": ["jpg", "webp", "avif"],
                "need_filter_image": False,
            }
            headers, cookies, trans_data = self.generate_request_params(
                cookies_str, api, data
            )
            response = requests.post(
                self.base_url + api,
                headers=headers,
                data=trans_data,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_homefeed_recommend_by_num(
        self, category, require_num, cookies_str: str, proxies: dict = None
    ):
        """
        根据数量获取主页推荐的笔记
        :param category: 你想要获取的频道
        :param require_num: 你想要获取的笔记的数量
        :param cookies_str: 你的cookies
        根据数量返回主页推荐的笔记
        """
        cursor_score, refresh_type, note_index = "", 1, 0
        note_list = []
        try:
            while True:
                success, msg, res_json = self.get_homefeed_recommend(
                    category,
                    cursor_score,
                    refresh_type,
                    note_index,
                    cookies_str,
                    proxies,
                )
                if not success:
                    raise Exception(msg)
                if "items" not in res_json["data"]:
                    break
                notes = res_json["data"]["items"]
                note_list.extend(notes)
                cursor_score = res_json["data"]["cursor_score"]
                refresh_type = 3
                note_index += 20
                if len(note_list) > require_num:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        if len(note_list) > require_num:
            note_list = note_list[:require_num]
        return success, msg, note_list

    def get_user_info(self, user_id: str, cookies_str: str, proxies: dict = None):
        """
        获取用户的信息
        :param user_id: 你想要获取的用户的id
        :param cookies_str: 你的cookies
        返回用户的信息
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/user/otherinfo"
            params = {"target_user_id": user_id}
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_self_info(self, cookies_str: str, proxies: dict = None):
        """
        获取用户自己的信息1
        :param cookies_str: 你的cookies
        返回用户自己的信息1
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/user/selfinfo"
            headers, cookies, data = self.generate_request_params(cookies_str, api)
            response = requests.get(
                self.base_url + api, headers=headers, cookies=cookies, proxies=proxies
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_self_info2(self, cookies_str: str, proxies: dict = None):
        """
        获取用户自己的信息2
        :param cookies_str: 你的cookies
        返回用户自己的信息2
        """
        res_json = None
        try:
            api = f"/api/sns/web/v2/user/me"
            headers, cookies, data = self.generate_request_params(cookies_str, api)
            response = requests.get(
                self.base_url + api, headers=headers, cookies=cookies, proxies=proxies
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_note_info(
        self,
        user_id: str,
        cursor: str,
        cookies_str: str,
        xsec_token="",
        xsec_source="",
        proxies: dict = None,
    ):
        """
        获取用户指定位置的笔记
        :param user_id: 你想要获取的用户的id
        :param cursor: 你想要获取的笔记的cursor
        :param cookies_str: 你的cookies
        返回用户指定位置的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/user_posted"
            params = {
                "num": "30",
                "cursor": cursor,
                "user_id": user_id,
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
            }
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_all_notes(self, user_url: str, cookies_str: str, proxies: dict = None):
        """
        获取用户所有笔记
        :param user_id: 你想要获取的用户的id
        :param cookies_str: 你的cookies
        返回用户的所有笔记
        """
        cursor = ""
        note_list = []
        try:
            urlParse = urllib.parse.urlparse(user_url)
            user_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split("&")
            kvDist = {kv.split("=")[0]: kv.split("=")[1] for kv in kvs}
            xsec_token = kvDist["xsec_token"] if "xsec_token" in kvDist else ""
            xsec_source = (
                kvDist["xsec_source"] if "xsec_source" in kvDist else "pc_search"
            )
            while True:
                success, msg, res_json = self.get_user_note_info(
                    user_id, cursor, cookies_str, xsec_token, xsec_source, proxies
                )
                if not success:
                    raise Exception(msg)
                notes = res_json["data"]["notes"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_list.extend(notes)
                if len(notes) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_list

    def get_user_like_note_info(
        self,
        user_id: str,
        cursor: str,
        cookies_str: str,
        xsec_token="",
        xsec_source="",
        proxies: dict = None,
    ):
        """
        获取用户指定位置喜欢的笔记
        :param user_id: 你想要获取的用户的id
        :param cursor: 你想要获取的笔记的cursor
        :param cookies_str: 你的cookies
        返回用户指定位置喜欢的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/note/like/page"
            params = {
                "num": "30",
                "cursor": cursor,
                "user_id": user_id,
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
            }
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_all_like_note_info(
        self, user_url: str, cookies_str: str, proxies: dict = None
    ):
        """
        获取用户所有喜欢笔记
        :param user_id: 你想要获取的用户的id
        :param cookies_str: 你的cookies
        返回用户的所有喜欢笔记
        """
        cursor = ""
        note_list = []
        try:
            urlParse = urllib.parse.urlparse(user_url)
            user_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split("&")
            kvDist = {kv.split("=")[0]: kv.split("=")[1] for kv in kvs}
            xsec_token = kvDist["xsec_token"] if "xsec_token" in kvDist else ""
            xsec_source = (
                kvDist["xsec_source"] if "xsec_source" in kvDist else "pc_user"
            )
            while True:
                success, msg, res_json = self.get_user_like_note_info(
                    user_id, cursor, cookies_str, xsec_token, xsec_source, proxies
                )
                if not success:
                    raise Exception(msg)
                notes = res_json["data"]["notes"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_list.extend(notes)
                if len(notes) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_list

    def get_user_collect_note_info(
        self,
        user_id: str,
        cursor: str,
        cookies_str: str,
        xsec_token="",
        xsec_source="",
        proxies: dict = None,
    ):
        """
        获取用户指定位置收藏的笔记
        :param user_id: 你想要获取的用户的id
        :param cursor: 你想要获取的笔记的cursor
        :param cookies_str: 你的cookies
        返回用户指定位置收藏的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v2/note/collect/page"
            params = {
                "num": "30",
                "cursor": cursor,
                "user_id": user_id,
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
            }
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_all_collect_note_info(
        self, user_url: str, cookies_str: str, proxies: dict = None
    ):
        """
        获取用户所有收藏笔记
        :param user_id: 你想要获取的用户的id
        :param cookies_str: 你的cookies
        返回用户的所有收藏笔记
        """
        cursor = ""
        note_list = []
        try:
            urlParse = urllib.parse.urlparse(user_url)
            user_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split("&")
            kvDist = {kv.split("=")[0]: kv.split("=")[1] for kv in kvs}
            xsec_token = kvDist["xsec_token"] if "xsec_token" in kvDist else ""
            xsec_source = (
                kvDist["xsec_source"] if "xsec_source" in kvDist else "pc_search"
            )
            while True:
                success, msg, res_json = self.get_user_collect_note_info(
                    user_id, cursor, cookies_str, xsec_token, xsec_source, proxies
                )
                if not success:
                    raise Exception(msg)
                notes = res_json["data"]["notes"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_list.extend(notes)
                if len(notes) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_list

    def get_note_info(self, url: str, cookies_str: str, proxies: dict = None):
        """
        获取笔记的详细
        :param url: 你想要获取的笔记的url
        :param cookies_str: 你的cookies
        :param xsec_source: 你的xsec_source 默认为pc_search pc_user pc_feed
        返回笔记的详细
        """
        res_json = None
        try:
            urlParse = urllib.parse.urlparse(url)
            note_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split("&")
            kvDist = {kv.split("=")[0]: kv.split("=")[1] for kv in kvs}
            api = f"/api/sns/web/v1/feed"
            data = {
                "source_note_id": note_id,
                "image_formats": ["jpg", "webp", "avif"],
                "extra": {"need_body_topic": "1"},
                "xsec_source": (
                    kvDist["xsec_source"] if "xsec_source" in kvDist else "pc_search"
                ),
                "xsec_token": kvDist["xsec_token"],
            }
            headers, cookies, data = self.generate_request_params(
                cookies_str, api, data
            )
            response = requests.post(
                self.base_url + api,
                headers=headers,
                data=data,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_search_keyword(self, word: str, cookies_str: str, proxies: dict = None):
        """
        获取搜索关键词
        :param word: 你的关键词
        :param cookies_str: 你的cookies
        返回搜索关键词
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/search/recommend"
            params = {"keyword": urllib.parse.quote(word)}
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def search_note(
        self,
        query: str,
        cookies_str: str,
        page=1,
        sort_type_choice=0,
        note_type=0,
        note_time=0,
        note_range=0,
        pos_distance=0,
        geo="",
        proxies: dict = None,
    ):
        """
        获取搜索笔记的结果
        :param query 搜索的关键词
        :param cookies_str 你的cookies
        :param page 搜索的页数
        :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
        :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
        :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
        :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
        :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
        返回搜索的结果
        """
        res_json = None
        sort_type = "general"
        if sort_type_choice == 1:
            sort_type = "time_descending"
        elif sort_type_choice == 2:
            sort_type = "popularity_descending"
        elif sort_type_choice == 3:
            sort_type = "comment_descending"
        elif sort_type_choice == 4:
            sort_type = "collect_descending"
        filter_note_type = "不限"
        if note_type == 1:
            filter_note_type = "视频笔记"
        elif note_type == 2:
            filter_note_type = "普通笔记"
        filter_note_time = "不限"
        if note_time == 1:
            filter_note_time = "一天内"
        elif note_time == 2:
            filter_note_time = "一周内"
        elif note_time == 3:
            filter_note_time = "半年内"
        filter_note_range = "不限"
        if note_range == 1:
            filter_note_range = "已看过"
        elif note_range == 2:
            filter_note_range = "未看过"
        elif note_range == 3:
            filter_note_range = "已关注"
        filter_pos_distance = "不限"
        if pos_distance == 1:
            filter_pos_distance = "同城"
        elif pos_distance == 2:
            filter_pos_distance = "附近"
        if geo:
            geo = json.dumps(geo, separators=(",", ":"))
        try:
            api = "/api/sns/web/v1/search/notes"
            data = {
                "keyword": query,
                "page": page,
                "page_size": 20,
                "search_id": self.generate_x_b3_traceid(21),
                "sort": "general",
                "note_type": 0,
                "ext_flags": [],
                "filters": [
                    {"tags": [sort_type], "type": "sort_type"},
                    {"tags": [filter_note_type], "type": "filter_note_type"},
                    {"tags": [filter_note_time], "type": "filter_note_time"},
                    {"tags": [filter_note_range], "type": "filter_note_range"},
                    {"tags": [filter_pos_distance], "type": "filter_pos_distance"},
                ],
                "geo": geo,
                "image_formats": ["jpg", "webp", "avif"],
            }
            headers, cookies, data = self.generate_request_params(
                cookies_str, api, data
            )
            response = requests.post(
                self.base_url + api,
                headers=headers,
                data=data.encode("utf-8"),
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def search_some_note(
        self,
        query: str,
        require_num: int,
        cookies_str: str,
        sort_type_choice=0,
        note_type=0,
        note_time=0,
        note_range=0,
        pos_distance=0,
        geo="",
        proxies: dict = None,
    ):
        """
        指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
        :param query 搜索的关键词
        :param require_num 搜索的数量
        :param cookies_str 你的cookies
        :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
        :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
        :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
        :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
        :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
        :param geo: 定位信息 经纬度
        返回搜索的结果
        """
        page = 1
        note_list = []
        try:
            while True:
                success, msg, res_json = self.search_note(
                    query,
                    cookies_str,
                    page,
                    sort_type_choice,
                    note_type,
                    note_time,
                    note_range,
                    pos_distance,
                    geo,
                    proxies,
                )
                if not success:
                    raise Exception(msg)
                if "items" not in res_json["data"]:
                    break
                notes = res_json["data"]["items"]
                note_list.extend(notes)
                page += 1
                if len(note_list) >= require_num or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        if len(note_list) > require_num:
            note_list = note_list[:require_num]
        return success, msg, note_list

    def search_user(self, query: str, cookies_str: str, page=1, proxies: dict = None):
        """
        获取搜索用户的结果
        :param query 搜索的关键词
        :param cookies_str 你的cookies
        :param page 搜索的页数
        返回搜索的结果
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/search/usersearch"
            data = {
                "search_user_request": {
                    "keyword": query,
                    "search_id": "2dn9they1jbjxwawlo4xd",
                    "page": page,
                    "page_size": 15,
                    "biz_type": "web_search_user",
                    "request_id": "22471139-1723999898524",
                }
            }
            headers, cookies, data = self.generate_request_params(
                cookies_str, api, data
            )
            response = requests.post(
                self.base_url + api,
                headers=headers,
                data=data.encode("utf-8"),
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def search_some_user(
        self, query: str, require_num: int, cookies_str: str, proxies: dict = None
    ):
        """
        指定数量搜索用户
        :param query 搜索的关键词
        :param require_num 搜索的数量
        :param cookies_str 你的cookies
        返回搜索的结果
        """
        page = 1
        user_list = []
        try:
            while True:
                success, msg, res_json = self.search_user(
                    query, cookies_str, page, proxies
                )
                if not success:
                    raise Exception(msg)
                if "users" not in res_json["data"]:
                    break
                users = res_json["data"]["users"]
                user_list.extend(users)
                page += 1
                if len(user_list) >= require_num or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        if len(user_list) > require_num:
            user_list = user_list[:require_num]
        return success, msg, user_list

    def get_note_out_comment(
        self,
        note_id: str,
        cursor: str,
        xsec_token: str,
        cookies_str: str,
        proxies: dict = None,
    ):
        """
        获取指定位置的笔记一级评论
        :param note_id 笔记的id
        :param cursor 指定位置的评论的cursor
        :param cookies_str 你的cookies
        返回指定位置的笔记一级评论
        """
        res_json = None
        try:
            api = "/api/sns/web/v2/comment/page"
            params = {
                "note_id": note_id,
                "cursor": cursor,
                "top_comment_id": "",
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token,
            }
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_note_all_out_comment(
        self, note_id: str, xsec_token: str, cookies_str: str, proxies: dict = None
    ):
        """
        获取笔记的全部一级评论
        :param note_id 笔记的id
        :param cookies_str 你的cookies
        返回笔记的全部一级评论
        """
        cursor = ""
        note_out_comment_list = []
        try:
            while True:
                success, msg, res_json = self.get_note_out_comment(
                    note_id, cursor, xsec_token, cookies_str, proxies
                )
                if not success:
                    raise Exception(msg)
                comments = res_json["data"]["comments"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_out_comment_list.extend(comments)
                if len(note_out_comment_list) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_out_comment_list

    def get_note_inner_comment(
        self,
        comment: dict,
        cursor: str,
        xsec_token: str,
        cookies_str: str,
        proxies: dict = None,
    ):
        """
        获取指定位置的笔记二级评论
        :param comment 笔记的一级评论
        :param cursor 指定位置的评论的cursor
        :param cookies_str 你的cookies
        返回指定位置的笔记二级评论
        """
        res_json = None
        try:
            api = "/api/sns/web/v2/comment/sub/page"
            params = {
                "note_id": comment["note_id"],
                "root_comment_id": comment["id"],
                "num": "10",
                "cursor": cursor,
                "image_formats": "jpg,webp,avif",
                "top_comment_id": "",
                "xsec_token": xsec_token,
            }
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_note_all_inner_comment(
        self, comment: dict, xsec_token: str, cookies_str: str, proxies: dict = None
    ):
        """
        获取笔记的全部二级评论
        :param comment 笔记的一级评论
        :param cookies_str 你的cookies
        返回笔记的全部二级评论
        """
        try:
            if not comment["sub_comment_has_more"]:
                return True, "success", comment
            cursor = comment["sub_comment_cursor"]
            inner_comment_list = []
            while True:
                success, msg, res_json = self.get_note_inner_comment(
                    comment, cursor, xsec_token, cookies_str, proxies
                )
                if not success:
                    raise Exception(msg)
                comments = res_json["data"]["comments"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                inner_comment_list.extend(comments)
                if not res_json["data"]["has_more"]:
                    break
            comment["sub_comments"].extend(inner_comment_list)
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, comment

    def get_note_all_comment(self, url: str, cookies_str: str, proxies: dict = None):
        """
        获取一篇文章的所有评论
        :param note_id: 你想要获取的笔记的id
        :param cookies_str: 你的cookies
        返回一篇文章的所有评论
        """
        out_comment_list = []
        try:
            urlParse = urllib.parse.urlparse(url)
            note_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split("&")
            kvDist = {kv.split("=")[0]: kv.split("=")[1] for kv in kvs}
            success, msg, out_comment_list = self.get_note_all_out_comment(
                note_id, kvDist["xsec_token"], cookies_str, proxies
            )
            if not success:
                raise Exception(msg)
            for comment in out_comment_list:
                success, msg, new_comment = self.get_note_all_inner_comment(
                    comment, kvDist["xsec_token"], cookies_str, proxies
                )
                if not success:
                    raise Exception(msg)
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, out_comment_list

    def get_unread_message(self, cookies_str: str, proxies: dict = None):
        """
        获取未读消息
        :param cookies_str: 你的cookies
        返回未读消息
        """
        res_json = None
        try:
            api = "/api/sns/web/unread_count"
            headers, cookies, data = self.generate_request_params(cookies_str, api)
            response = requests.get(
                self.base_url + api, headers=headers, cookies=cookies, proxies=proxies
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_metions(self, cursor: str, cookies_str: str, proxies: dict = None):
        """
        获取评论和@提醒
        :param cursor: 你想要获取的评论和@提醒的cursor
        :param cookies_str: 你的cookies
        返回评论和@提醒
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/you/mentions"
            params = {"num": "20", "cursor": cursor}
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_all_metions(self, cookies_str: str, proxies: dict = None):
        """
        获取全部的评论和@提醒
        :param cookies_str: 你的cookies
        返回全部的评论和@提醒
        """
        cursor = ""
        metions_list = []
        try:
            while True:
                success, msg, res_json = self.get_metions(cursor, cookies_str, proxies)
                if not success:
                    raise Exception(msg)
                metions = res_json["data"]["message_list"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                metions_list.extend(metions)
                if not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, metions_list

    def get_likesAndcollects(self, cursor: str, cookies_str: str, proxies: dict = None):
        """
        获取赞和收藏
        :param cursor: 你想要获取的赞和收藏的cursor
        :param cookies_str: 你的cookies
        返回赞和收藏
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/you/likes"
            params = {"num": "20", "cursor": cursor}
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_all_likesAndcollects(self, cookies_str: str, proxies: dict = None):
        """
        获取全部的赞和收藏
        :param cookies_str: 你的cookies
        返回全部的赞和收藏
        """
        cursor = ""
        likesAndcollects_list = []
        try:
            while True:
                success, msg, res_json = self.get_likesAndcollects(
                    cursor, cookies_str, proxies
                )
                if not success:
                    raise Exception(msg)
                likesAndcollects = res_json["data"]["message_list"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                likesAndcollects_list.extend(likesAndcollects)
                if not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, likesAndcollects_list

    def get_new_connections(self, cursor: str, cookies_str: str, proxies: dict = None):
        """
        获取新增关注
        :param cursor: 你想要获取的新增关注的cursor
        :param cookies_str: 你的cookies
        返回新增关注
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/you/connections"
            params = {"num": "20", "cursor": cursor}
            splice_api = self.splice_str(api, params)
            headers, cookies, data = self.generate_request_params(
                cookies_str, splice_api
            )
            response = requests.get(
                self.base_url + splice_api,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
            )
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_all_new_connections(self, cookies_str: str, proxies: dict = None):
        """
        获取全部的新增关注
        :param cookies_str: 你的cookies
        返回全部的新增关注
        """
        cursor = ""
        connections_list = []
        try:
            while True:
                success, msg, res_json = self.get_new_connections(
                    cursor, cookies_str, proxies
                )
                if not success:
                    raise Exception(msg)
                connections = res_json["data"]["message_list"]
                if "cursor" in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                connections_list.extend(connections)
                if not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, connections_list

    def get_note_no_water_video(self, note_id):
        """
        获取笔记无水印视频
        :param note_id: 你想要获取的笔记的id
        返回笔记无水印视频
        """
        success = True
        msg = "成功"
        video_addr = None
        try:
            headers = self.get_common_headers()
            url = f"https://www.xiaohongshu.com/explore/{note_id}"
            response = requests.get(url, headers=headers)
            res = response.text
            video_addr = re.findall(r'<meta name="og:video" content="(.*?)">', res)[0]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, video_addr

    @staticmethod
    def get_note_no_water_img(img_url):
        """
        获取笔记无水印图片
        :param img_url: 你想要获取的图片的url
        返回笔记无水印图片
        """
        success = True
        msg = "成功"
        new_url = None
        try:
            # https://sns-webpic-qc.xhscdn.com/202403211626/c4fcecea4bd012a1fe8d2f1968d6aa91/110/0/01e50c1c135e8c010010000000018ab74db332_0.jpg!nd_dft_wlteh_webp_3
            if ".jpg" in img_url:
                img_id = "/".join([split for split in img_url.split("/")[-3:]]).split(
                    "!"
                )[0]
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/1920/format/png"
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/format/png"
                # return f'https://sns-img-hw.xhscdn.com/{img_id}'
                new_url = f"https://sns-img-qc.xhscdn.com/{img_id}"

            # 'https://sns-webpic-qc.xhscdn.com/202403231640/ea961053c4e0e467df1cc93afdabd630/spectrum/1000g0k0200n7mj8fq0005n7ikbllol6q50oniuo!nd_dft_wgth_webp_3'
            elif "spectrum" in img_url:
                img_id = "/".join(img_url.split("/")[-2:]).split("!")[0]
                # return f'http://sns-webpic.xhscdn.com/{img_id}?imageView2/2/w/1920/format/jpg'
                new_url = (
                    f"http://sns-webpic.xhscdn.com/{img_id}?imageView2/2/w/format/jpg"
                )
            else:
                # 'http://sns-webpic-qc.xhscdn.com/202403181511/64ad2ea67ce04159170c686a941354f5/1040g008310cs1hii6g6g5ngacg208q5rlf1gld8!nd_dft_wlteh_webp_3'
                img_id = img_url.split("/")[-1].split("!")[0]
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/1920/format/png"
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/format/png"
                # return f'https://sns-img-hw.xhscdn.com/{img_id}'
                new_url = f"https://sns-img-qc.xhscdn.com/{img_id}"
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, new_url
