#!/usr/bin/env python3
"""Terminal client for submitting projects to cannjudge.cn.

Examples:
  python3 cannjudge_cli.py login
  python3 cannjudge_cli.py submit ./project
  python3 cannjudge_cli.py submit ./project --contest op_challenge_hangxia_prelim \
      --problem quantmatmulreluquant --wait 5
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import http.cookiejar
import http.cookies
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_BASE = "https://cannjudge.cn"
DEFAULT_CONTEST = "op_challenge_hangxia_prelim"
DEFAULT_PROBLEM = "quantmatmulreluquant"
DEFAULT_SESSION = pathlib.Path.home() / ".config" / "cannjudge" / "cookies.lwp"
DEFAULT_TEAM_FILE = pathlib.Path(__file__).resolve().parent.parent / "team.txt"
DEFAULT_USER_ID_FILE = pathlib.Path(__file__).resolve().parent / "userid.txt"


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str, payload=None):
        super().__init__(f"HTTP {status}: {message}")
        self.status, self.payload = status, payload


class Client:
    def __init__(self, base: str, cookie_file: pathlib.Path):
        self.base = base.rstrip("/")
        self.cookie_file = cookie_file
        self.jar = http.cookiejar.LWPCookieJar(str(cookie_file))
        self.cookie_file_format = "lwp"
        if cookie_file.exists():
            try:
                self.jar.load(ignore_discard=True, ignore_expires=True)
            except (OSError, http.cookiejar.LoadError):
                # A browser's copied Request Headers > Cookie value is a
                # convenient session-file format too.  Do not require users
                # to convert it to Netscape/LWP format first.
                try:
                    raw = cookie_file.read_text(encoding="utf-8").strip()
                    self._load_raw_cookie(raw)
                    self.cookie_file_format = "raw"
                except (OSError, UnicodeDecodeError, RuntimeError):
                    print(f"警告：无法读取 Cookie 文件 {cookie_file}，将重新登录", file=sys.stderr)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def _load_raw_cookie(self, raw: str):
        if raw.lower().startswith("cookie:"):
            raw = raw.split(":", 1)[1].strip()
        if not raw or "\n" in raw or "\r" in raw:
            raise RuntimeError("Cookie 文件必须是单行 Cookie 请求头值")
        cookies = http.cookies.SimpleCookie()
        try:
            cookies.load(raw)
        except http.cookies.CookieError as exc:
            raise RuntimeError("Cookie 文件格式无效") from exc
        if not cookies:
            raise RuntimeError("Cookie 文件中没有可解析的 Cookie")
        origin = urllib.parse.urlsplit(self.base)
        if origin.scheme != "https" or not origin.hostname:
            raise RuntimeError("Cookie 文件只支持 HTTPS 站点")
        self.jar.clear()
        for name, morsel in cookies.items():
            self.jar.set_cookie(http.cookiejar.Cookie(
                version=0, name=name, value=morsel.value, port=None,
                port_specified=False, domain=origin.hostname,
                domain_specified=False, domain_initial_dot=False,
                path="/", path_specified=True, secure=True, expires=None,
                discard=True, comment=None, comment_url=None,
                rest={"HttpOnly": None}, rfc2109=False,
            ))

    def save_cookies(self):
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        if self.cookie_file_format == "raw":
            # Keep a copied-cookie session file usable/editable as plain text.
            raw = "; ".join(f"{cookie.name}={cookie.value}" for cookie in self.jar)
            self.cookie_file.write_text(raw + "\n", encoding="utf-8")
        else:
            self.jar.save(ignore_discard=True, ignore_expires=True)
        os.chmod(self.cookie_file, 0o600)

    def request(self, path: str, method="GET", data=None, query=None):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        body = None
        headers = {"Accept": "application/json", "User-Agent": "cannjudge-cli/1.0"}
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=30) as response:
                raw = response.read()
                text = raw.decode("utf-8", errors="replace")
                if not text:
                    return {}
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"message": text}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"message": raw}
            msg = (payload.get("message") or payload.get("msg") or payload.get("error")
                   or payload.get("detail") or f"请求失败({exc.code})") if isinstance(payload, dict) else str(payload)
            raise ApiError(exc.code, str(msg), payload) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"网络请求失败：{exc.reason}") from exc


def obj_id(value):
    return str(value.get("_id") or value.get("id") or "") if isinstance(value, dict) else str(value)


def load_team_name(path=DEFAULT_TEAM_FILE):
    """Read the local team name used as the default ranking search query."""
    try:
        team = pathlib.Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise RuntimeError(f"无法读取队伍名称文件：{path}") from exc
    if not team:
        raise RuntimeError(f"队伍名称文件为空：{path}")
    return team


def load_user_id(path=DEFAULT_USER_ID_FILE):
    """Read the local CANNJudge user ID used for submissions and rankings."""
    try:
        user_id = pathlib.Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise RuntimeError(f"未找到 userId 文件：{path}；请使用 --user-id 指定") from None
    except OSError as exc:
        raise RuntimeError(f"无法读取 userId 文件：{path}") from exc
    if not user_id:
        raise RuntimeError(f"userId 文件为空：{path}")
    return user_id


def import_cookie(client: Client):
    """Import only the judge site's Cookie header, not third-party credentials."""
    origin = urllib.parse.urlsplit(client.base)
    if origin.scheme != "https" or not origin.hostname:
        raise RuntimeError("Cookie 导入只支持 HTTPS 站点")
    print(f"请粘贴 {origin.hostname} 登录后 API 请求中的 Cookie 请求头值。")
    print("不要粘贴 GitLab/GitCode 的 Cookie、密码或访问令牌。输入不会回显。")
    raw = getpass.getpass("Cookie：").strip()
    if raw.lower().startswith("cookie:"):
        raw = raw.split(":", 1)[1].strip()
    if not raw or "\n" in raw or "\r" in raw:
        raise RuntimeError("请输入单行 Cookie 请求头值")
    cookies = http.cookies.SimpleCookie()
    try:
        cookies.load(raw)
    except http.cookies.CookieError as exc:
        raise RuntimeError("Cookie 格式无效") from exc
    if not cookies:
        raise RuntimeError("未解析到 Cookie")
    # Replace the in-memory jar only after parsing; never send cookies to the
    # third-party identity provider. Server authentication is checked on submit.
    client._load_raw_cookie(raw)
    client.cookie_file_format = "raw"
    client.save_cookies()
    print("Cookie 已导入为纯文本 Cookie 文件（尚未验证登录状态）；可运行 submit 提交。")


def get_problem(client: Client, contest_name: str, problem_name: str):
    group = client.request("/api/groups/public")
    gid = obj_id(group)
    if not gid:
        raise RuntimeError("无法获取公共小组")
    contest = client.request("/api/contests/name/" + urllib.parse.quote(contest_name, safe=""),
                             query={"groupId": gid})
    cid = obj_id(contest)
    if not cid:
        raise RuntimeError(f"找不到赛事：{contest_name}")
    # Prefer the exact name endpoint; fall back to the contest list for installations
    # that do not expose /api/problems/name.
    try:
        problem = client.request("/api/problems/name/" + urllib.parse.quote(problem_name, safe=""),
                                 query={"contestId": cid})
    except ApiError:
        problems = client.request(f"/api/problems/contest/{urllib.parse.quote(cid, safe='')}")
        problem = next((p for p in (problems if isinstance(problems, list) else [])
                        if problem_name in {str(p.get("name", "")), str(p.get("canonical_name", "")),
                                            str(p.get("title", ""))}), None)
    if not problem:
        raise RuntimeError(f"找不到题目：{problem_name}")
    return group, contest, problem


def login(client: Client, account: str | None = None):
    account = account or input("账号（邮箱/手机号）：").strip()
    password = getpass.getpass("密码：")
    captcha = client.request("/api/users/captcha")
    image = str(captcha.get("image", ""))
    image_path = client.cookie_file.parent / "captcha"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if image.startswith("data:") and "," in image:
        meta, encoded = image.split(",", 1)
        suffix = ".svg" if "svg" in meta else ".png"
        image_path = image_path.with_suffix(suffix)
        image_path.write_bytes(base64.b64decode(encoded))
        print(f"验证码图片已保存到：{image_path}")
    elif "<svg" in image:
        image_path = image_path.with_suffix(".svg")
        image_path.write_text(image, encoding="utf-8")
        print(f"验证码图片已保存到：{image_path}")
    elif image:
        raise RuntimeError("无法识别网站返回的验证码格式")
    code = input("图形验证码：").strip()
    login_type = "phone" if account.isdigit() else "email"
    user = client.request("/api/users/login", "POST", {
        "loginType": login_type, "account": account, "password": password,
        "captchaId": captcha.get("captchaId"), "captchaCode": code,
    })
    client.save_cookies()
    print(f"登录成功：{user.get('nickname') or user.get('email') or user.get('ID', '')}")


def collect_files(root: pathlib.Path, template_files):
    if not root.is_dir():
        raise RuntimeError(f"工程目录不存在：{root}")
    result = []
    missing = []
    for entry in template_files:
        if entry.get("editable") is False:
            continue
        rel = entry.get("path")
        if not isinstance(rel, str) or not rel:
            raise RuntimeError("模板文件路径无效")
        path = (root / rel).resolve()
        if pathlib.PurePosixPath(rel).is_absolute() or not path.is_relative_to(root.resolve()):
            raise RuntimeError(f"模板文件路径超出工程目录：{rel}")
        if not path.is_file():
            missing.append(rel)
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise RuntimeError(f"可编辑模板文件不是 UTF-8：{rel}") from None
        result.append({"path": rel, "content": content})
    if missing:
        raise RuntimeError("缺少可编辑模板文件：" + ", ".join(missing))
    if not result:
        raise RuntimeError("没有可编辑的模板源文件")
    return result


def file_manifest(files, contest, problem, problem_id, template):
    """Return a secret-free record of the exact editable payload.

    File contents stay in the submission request and are never copied into the
    manifest.  The manifest is useful even when a later result is incomplete.
    """
    return {
        "schema_version": 1,
        "contest": contest,
        "problem": problem,
        "problem_id": problem_id,
        "template_files": [
            {"path": entry.get("path"), "editable": entry.get("editable", True)}
            for entry in template
        ],
        "files": {
            entry["path"]: {
                "sha256": hashlib.sha256(entry["content"].encode("utf-8")).hexdigest(),
                "bytes": len(entry["content"].encode("utf-8")),
            }
            for entry in files
        },
    }


def submit(client: Client, args):
    user_id = args.user_id or load_user_id()
    group, contest, problem = get_problem(client, args.contest, args.problem)
    pid = obj_id(problem)
    if not pid:
        raise RuntimeError("题目信息中没有有效 ID，已停止提交")
    template = client.request(f"/api/problems/{urllib.parse.quote(pid, safe='')}/template")
    template_files = template.get("data", {}).get("files", [])
    if not template_files:
        raise RuntimeError("无法获取工程模板文件列表；为防止误提交，已停止")
    files = collect_files(pathlib.Path(args.project).expanduser().resolve(), template_files)
    manifest = file_manifest(files, args.contest, args.problem, pid, template_files)
    expected_project = getattr(args, 'expected_project', None)
    if expected_project:
        expected = json.loads(pathlib.Path(expected_project).read_text())
        root = pathlib.Path(args.project).resolve()
        for name, expected_hash in expected.items():
            path = (root / name).resolve()
            if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                raise RuntimeError('Fast Track project identity mismatch')
        if any(entry['path'] not in expected or manifest['files'][entry['path']]['sha256'] != expected[entry['path']] for entry in files):
            raise RuntimeError('Dynamic editable payload differs from qualified project')
        # Persist BEFORE the POST, including when the response times out.
        preflight = pathlib.Path(args.output).with_suffix('.manifest.json')
        preflight.parent.mkdir(parents=True, exist_ok=True)
        preflight.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    payload = {
        "userId": user_id, "problemId": pid, "files": files,
        "tiling_h": "", "tiling_key_h": "", "host_cpp": "", "kernel_cpp": "",
    }
    print(f"提交 {len(files)} 个文件到：{problem.get('title') or args.problem}")
    response = client.request("/api/submissions/submit", "POST", payload)
    data = response.get("data", response) if isinstance(response, dict) else response
    submission_id = str(data.get("submissionId") or data.get("_id") or data.get("id") or "")
    if not submission_id:
        raise RuntimeError(f"提交成功但响应中没有 submissionId：{response}")
    print(f"提交成功，ID：{submission_id}")
    result_path = pathlib.Path(args.output or f"cannjudge-result-{submission_id}.json").expanduser()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result_path.with_suffix(".submit.json").write_text(
        json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    watch(client, submission_id, result_path, args.wait, args.timeout)
    if args.ranking_query is not None:
        try:
            ranking(client, pid, args.ranking_query, user_id,
                    result_path.with_suffix(".ranking.json"), submission_id)
        except (ApiError, RuntimeError, OSError) as exc:
            print(f"评测结果已保存，但排行榜查询失败：{exc}", file=sys.stderr)
    return 0


def ranking(client, problem_id, query, user_id, output, submission_id=None):
    rows = []
    page = 1
    while True:
        response = client.request(
            f"/api/problems/{urllib.parse.quote(problem_id, safe='')}/ranking",
            query={"page": page, "size": 20, "q": query})
        if not isinstance(response, dict) or not isinstance(response.get("rows"), list):
            raise RuntimeError("排行榜响应缺少 rows 列表")
        rows.extend(row for row in response["rows"]
                    if str(row.get("user_id") or row.get("user", {}).get("_id") or "") == user_id)
        if page >= int(response.get("pages", 1)) or not response["rows"]:
            break
        page += 1
    metrics = [{"rank": row.get("rank"), "score": row.get("score"),
                "user_id": user_id, "submission_id": row.get("submission_id"),
                "status": row.get("status"),
                "matches_requested_submission": (row.get("submission_id") == submission_id)
                if submission_id else None} for row in rows]
    snapshot = {"problem_id": problem_id, "query": query,
                "queried_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "requested_submission_id": submission_id, "metrics": metrics}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    if not metrics:
        print("排行榜未找到该用户；可能尚未更新或搜索词不匹配。")
    for item in metrics:
        print(f"排行榜：rank={item['rank']}，score={item['score']}，"
              f"submission_id={item['submission_id']}")
        if item["matches_requested_submission"] is False:
            print("注意：排行榜记录不是本次提交，可能是历史最佳成绩或尚未更新。")
    print(f"排行榜指标已保存：{output}")
    return snapshot


def watch(client, submission_id, result_path, interval, timeout):
    result_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    latest = None
    while True:
        latest = client.request(f"/api/submissions/{urllib.parse.quote(submission_id, safe='')}")
        result_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
        status = str(latest.get("status", "")) if isinstance(latest, dict) else ""
        print(f"[{time.strftime('%H:%M:%S')}] 状态：{status or '未知'}", flush=True)
        if status.lower() not in {"waiting", "pending", "judging", "running", "processing", "queued"}:
            break
        if timeout and time.time() - started >= timeout:
            print("达到等待超时，保存当前结果。", file=sys.stderr)
            break
        time.sleep(interval)
    result_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"测试结果已保存：{result_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="CANNJudge 终端登录、提交与结果保存工具")
    parser.add_argument("--base", default=DEFAULT_BASE, help="站点地址，默认 https://cannjudge.cn")
    parser.add_argument("--session", default=str(DEFAULT_SESSION), help="Cookie 文件路径")
    sub = parser.add_subparsers(dest="command", required=True)
    lp = sub.add_parser("login", help="交互式登录并保存 Cookie")
    lp.add_argument("--account", help="账号；不提供则交互输入")
    sub.add_parser("import-cookie", help="导入第三方登录后的 CANNJudge Cookie（隐藏输入）")
    sp = sub.add_parser("submit", help="提交工程并等待评测")
    sp.add_argument("project", help="工程目录")
    sp.add_argument("--user-id", help="当前登录账号的 userId；未指定时读取 gitlabcann/userid.txt")
    sp.add_argument("--contest", default=DEFAULT_CONTEST)
    sp.add_argument("--problem", default=DEFAULT_PROBLEM)
    sp.add_argument("--output", help="结果 JSON 输出路径")
    sp.add_argument('--expected-project', help='Fast Track qualified project hash map; checked before POST')
    sp.add_argument("--wait", type=float, default=3, help="轮询间隔秒数，默认 3")
    sp.add_argument("--timeout", type=float, default=0, help="等待超时秒数，0 表示一直等待")
    sp.add_argument("--ranking-query", help="评测查询结束后查询排行榜的搜索词，例如队名关键字")
    rk = sub.add_parser("ranking", help="查询用户的排行榜 rank 和 score，不提交代码")
    rk.add_argument("--problem-id", required=True)
    rk.add_argument("--user-id", help="当前登录账号的 userId；未指定时读取 gitlabcann/userid.txt")
    rk.add_argument("--query", help="排行榜搜索词；未指定时读取项目根目录 team.txt")
    rk.add_argument("--submission-id", help="可选，用于核对排行榜是否对应指定提交")
    rk.add_argument("--output", default="cannjudge-ranking.json")
    rp = sub.add_parser("result", help="重新获取已有提交的评测结果，不会重复提交")
    rp.add_argument("submission_id")
    rp.add_argument("--output", help="结果 JSON 输出路径")
    rp.add_argument("--wait", type=float, default=3)
    rp.add_argument("--timeout", type=float, default=0)
    args = parser.parse_args()
    if args.command in {"submit", "result"} and (args.wait < 1 or args.timeout < 0):
        parser.error("--wait 必须至少为 1，--timeout 不能为负数")
    client = Client(args.base, pathlib.Path(args.session).expanduser())
    try:
        if args.command == "login":
            login(client, args.account)
        elif args.command == "import-cookie":
            import_cookie(client)
        elif args.command == "submit":
            submit(client, args)
        elif args.command == "ranking":
            query = args.query if args.query is not None else load_team_name()
            if not query:
                raise RuntimeError("未指定排行榜搜索词，且项目根目录没有有效 team.txt")
            user_id = args.user_id or load_user_id()
            ranking(client, args.problem_id, query, user_id,
                    pathlib.Path(args.output).expanduser(), args.submission_id)
        else:
            watch(client, args.submission_id,
                  pathlib.Path(args.output or f"cannjudge-result-{args.submission_id}.json").expanduser(),
                  args.wait, args.timeout)
    except KeyboardInterrupt:
        print("\n已中断。可用 result <提交ID> 继续获取结果，无需重新提交。", file=sys.stderr)
        return 130
    except (ApiError, RuntimeError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        if isinstance(exc, ApiError) and exc.status in (401, 403):
            print("提示：登录失效可运行 login；第三方登录请运行 import-cookie 更新 CANNJudge Cookie。403 也可能是参赛权限不足。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
