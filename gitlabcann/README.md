# CANNJudge 终端提交工具

这是一个不依赖第三方 Python 包的终端客户端，支持：

- 交互式账号、密码、图形验证码登录；
- 支持直接读取浏览器复制的 Cookie 值文件，也支持 LWP Cookie 文件；
- 从本地工程目录读取 UTF-8 源文件并提交；
- 自动轮询评测状态；
- 将完整提交详情（包括测试点状态、耗时、错误信息等）保存为 JSON。

## 使用

### GitLab / GitCode 等第三方登录

`login` 子命令仅用于站点自己的账号密码登录，不能输入 GitLab 的账号密码。
第三方登录请导入登录完成后的 **CANNJudge 会话 Cookie**：

1. 在浏览器中通过你原来的第三方入口登录 CANNJudge。
2. 在 CANNJudge 页面按 F12 打开开发者工具，进入 **Network（网络）**，刷新页面。
3. 选择一个发往 `https://cannjudge.cn/api/...` 的请求，在 **Request Headers（请求头）** 中复制 `Cookie` 的值。不要复制第三方登录站点的 Cookie，也不要复制响应里的 `Set-Cookie`。
4. 在终端运行以下命令，按提示粘贴（不回显）：

```bash
python3 cannjudge_cli.py import-cookie
python3 cannjudge_cli.py submit /path/to/your/project --output results/run-1.json
```

也可以把浏览器复制的 **Cookie 请求头值**直接保存到文件，例如项目目录下的
文件名为 `cookie`。文件内容应为一行 `name=value; name2=value2`，不要包含
`Set-Cookie`、密码或令牌。提交时指定该文件：

```bash
python3 cannjudge_cli.py --session ./cookie submit /path/to/your/project \
  --output results/run-1.json
```

提交所需的 `userId` 默认从 `gitlabcann/userid.txt` 读取；也可以用
`--user-id` 临时覆盖。该文件当前保存本账号的 userId，不是登录 Cookie。

客户端会自动识别纯文本 Cookie 文件；不需要先转换成 LWP 格式。纯文本
Cookie 文件会在需要保存时保持为纯文本，权限会设置为仅当前用户可读写（600）。
如果文件名不是 `cookie`，将命令中的 `./cookie` 替换为实际路径即可。

只需首次导入，Cookie 过期后再更新。Cookie 等同于登录凭证，不要发到聊天、提交进代码仓库或直接放在 shell 命令行参数里。导入只检查格式，真实会话和参赛权限由服务端在后续请求时校验。

这是复用第三方登录后的会话，不是实现 GitLab OAuth；当前检查到的网站公开前端提供 GitCode/华为入口，未见 GitLab 入口。如你的登录页面不同，请以实际页面为准。

### 站点账号密码登录

```bash
chmod +x cannjudge_cli.py
python3 cannjudge_cli.py login
python3 cannjudge_cli.py submit /path/to/your/project
```

题目和赛事默认就是用户给出的地址对应的：

```text
赛事：op_challenge_hangxia_prelim
题目：quantmatmulreluquant
```

也可以显式指定：

```bash
python3 cannjudge_cli.py submit ./my-op \
  --contest op_challenge_hangxia_prelim \
  --problem quantmatmulreluquant \
  --output results/submit-1.json \
  --wait 5
```

若登录过期，重新执行 `login` 即可；使用浏览器 Cookie 文件时，重新复制最新 Cookie 值覆盖该文件即可。验证码图片写到 Cookie 所在目录，终端会显示路径；用图片查看器打开后人工输入验证码（不绕过验证码）。远程 SSH 环境可以把图片下载到本地查看。Cookie 文件权限为仅当前用户可读写（600）。工具不保存密码。

网络断开或手动中断后，可以按提交 ID 恢复结果查询，不会再次提交代码：

```bash
python3 cannjudge_cli.py result <提交ID> --output results/submit-1.json
```

结果每次轮询都会保存；首次提交响应另存为 `*.submit.json`。若提交请求超时，先去提交记录确认是否已受理，不要直接重试，避免重复提交。

## 排行榜指标

项目根目录的 `team.txt` 保存默认队伍名称（当前为 `西西里 的队伍`）。运行
`ranking` 时不指定 `--query` 将自动读取该文件；也可以显式指定搜索词覆盖默认值。

可单独查询排行榜中的 `rank` 和 `score`，不触发新提交：

```bash
python3 cannjudge_cli.py ranking \
  --problem-id <题目ID> \
  --submission-id <提交ID> \
  --output results/ranking.json
```

排行榜查询也默认从 `gitlabcann/userid.txt` 读取用户 ID；需要查询其他账号时，
可添加 `--user-id <当前用户ID>` 覆盖默认值。提交命令同样支持该选项。

脚本按用户 ID 匹配排行榜结果，并保存 `rank`、`score`、状态及榜单中的
`submission_id`。排行榜可能显示历史最佳记录；提供 `--submission-id` 后会标记
该记录是否对应指定提交。提交完成后也可用 `submit --ranking-query '队伍名称关键字'`
自动查询，结果保存为与提交结果同目录的 `*.ranking.json`。

## 工程文件

请使用该题下载的完整模板工程作为目录。工具根据服务端模板仅提交可编辑文件，缺失必需文件时会停止，不会上传无关文档、只读文件或构建产物。当前版本不提交模板之外的自定义新增文件。会跳过隐藏文件、`.git`、`build`、`out` 和 `__pycache__` 目录，以及无法按 UTF-8 解码的文件。

需要 Python 3.10+。接口依据网站当前公开前端实现，网站升级后可能需要适配。命令行参数和静态上传流程已核对。2026-10-16 曾有一次历史提交结果被离线复核，其提交 ID、15/15 状态、score、editable 文件清单及 hash 记录在项目根目录 `report.md`；本次核查未重新登录、提交或轮询。Cookie 仍为敏感凭证，不应读取、回显或纳入版本库。
