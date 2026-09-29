#!/usr/bin/env python3
"""
敲敲云 skill（lowapp / miniflow / dashboard）的临时目录 —— **一次建应用 = 一个工作目录**。

    {系统临时目录}/jeecg-lowcode/
    ├── <英文简称>_<yyyyMMdd-HHmmss>/   一次建应用的全部文件（并行多个代理各开各的，互不干扰）
    │   ├── app.json                    {slug, created, app_id, app_name, tenant_id}；build_app 建出应用后自动回填
    │   ├── app_spec.json flows.py …    手写配置
    │   └── build/ patch/ layout/ link/ export/ dash/ probe.json …   脚本产物
    ├── <app_id>/                       没有工作目录时（直接改已有应用）脚本产物的兜底
    ├── _jobs/                          一次性小任务的配置（文件名自动加时间戳前缀，不会撞名）
    ├── _cache/                         跨应用短 TTL 缓存（内部按 key 区分）
    └── _noapp/                         连 app_id 都没有时的兜底

后面的脚本手里只有 app_id：`app_workdir(app_id)` 扫各工作目录的 app.json 找回同一个目录，
所以 `--from` 续跑、建后套件重跑、换一个会话接着改，都落回原处。

CLI:
    python skill_temp_path.py --new crm                   # 开工作目录，打印路径（建应用第一步；简称用英文）
    python skill_temp_path.py --new crm -f app_spec.json  # 开工作目录并返回其中的文件路径
    python skill_temp_path.py --app-id <id> --sub patch -f x.json
    python skill_temp_path.py -f job.json                 # 一次性小任务：_jobs/<时间戳>_job.json
    python skill_temp_path.py --self-test                 # 改本文件后必跑：隔离目录里自检全部规则，不碰真实目录、不联网

Output:
    On success: a single line containing the absolute path, written to stdout.
    On failure: a one-line error message to stderr; exit code 1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import uuid

DEFAULT_SKILL_NAME = "jeecg-lowcode"
ROOT = os.path.join(tempfile.gettempdir(), DEFAULT_SKILL_NAME)
APP_FILE = "app.json"
ENV_WORKDIR = "JEECG_LOWCODE_WORKDIR"   # 显式指定工作目录（优先级最高）


def _check(label: str, part) -> None:
    part = None if part is None else str(part)
    if part and (any(sep in part for sep in ("/", "\\", "..")) or not part.isascii()):
        raise ValueError(f"invalid {label} (bare ASCII name only): {part!r}")


def _load(d: str) -> dict | None:
    try:
        with open(os.path.join(d, APP_FILE), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _norm(p: str) -> str:
    """比较用的规范路径：Windows 上大小写不敏感、8.3 短名（ZHANG~1）要展开，否则同一目录判成两个。"""
    return os.path.normcase(os.path.realpath(p))


def new_workspace(slug: str) -> str:
    """开一个工作目录 <slug>_<yyyyMMdd-HHmmss>/ 并写 app.json。slug 只收 ASCII（应用名的英文简称，如 crm）。"""
    if not slug:
        raise ValueError("slug 不能为空：传应用名的英文简称，如 crm / jxc / sales")
    _check("slug", slug)
    base = "%s_%s" % (slug, time.strftime("%Y%m%d-%H%M%S"))
    d = os.path.join(ROOT, base)
    n = 2
    while os.path.exists(d):
        d = os.path.join(ROOT, "%s-%d" % (base, n))
        n += 1
    os.makedirs(d)
    with open(os.path.join(d, APP_FILE), "w", encoding="utf-8") as fh:
        json.dump({"slug": slug, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "app_id": None},
                  fh, ensure_ascii=False, indent=1)
    return d


def workspace_of(path: str | None) -> str | None:
    """path（文件或目录）所在的工作目录：从它往上找第一个带 app.json 的目录（不越过 ROOT）。"""
    if not path:
        return None
    d = os.path.realpath(path if os.path.isdir(path) else os.path.dirname(path))
    root = _norm(ROOT)
    while (_norm(d) + os.sep).startswith(root + os.sep) and _norm(d) != root:
        if _load(d) is not None:
            return d
        d = os.path.dirname(d)
    return None


def bind_workspace(path: str | None, app_id, app_name=None, tenant_id=None) -> str | None:
    """把 app_id 写进 path 所在工作目录的 app.json。一个工作目录只对应一个应用：已绑别的应用就报错。"""
    d = workspace_of(path)
    if not d:
        return None
    j = _load(d) or {}
    old = j.get("app_id")
    if old and str(old) != str(app_id):
        raise SystemExit(f"FAIL: 工作目录 {d} 已绑定应用 {old}，不能再绑 {app_id} —— "
                         f"新应用请另开工作目录（skill_temp_path.py --new <英文简称>）")
    j["app_id"] = str(app_id)
    if app_name:
        j["app_name"] = app_name
    if tenant_id is not None:
        j["tenant_id"] = str(tenant_id)
    with open(os.path.join(d, APP_FILE), "w", encoding="utf-8") as fh:
        json.dump(j, fh, ensure_ascii=False, indent=1)
    return d


def find_workspace(app_id) -> str | None:
    """按 app_id 反查工作目录（多个时取最新创建的一个）。"""
    if not app_id or not os.path.isdir(ROOT):
        return None
    hits = []
    for name in os.listdir(ROOT):
        d = os.path.join(ROOT, name)
        j = _load(d) if os.path.isdir(d) else None
        if j and str(j.get("app_id")) == str(app_id):
            hits.append((j.get("created") or "", name, d))
    return max(hits)[2] if hits else None


def app_workdir(app_id=None, sub: str | None = None, create: bool = True) -> str:
    """脚本产物目录：JEECG_LOWCODE_WORKDIR > app_id 所属工作目录 > jeecg-lowcode/<app_id> > _noapp。

    create=False：只算路径不建目录 —— 给「只读上一步产物」的脚本用，app_id 写错时
    不会在根目录下留一个空的 <app_id>/（2026-09-24 实测：试探参数时造出 jeecg-lowcode/0/）。"""
    _check("app id", app_id)
    _check("sub dir", sub)
    env = (os.environ.get(ENV_WORKDIR) or "").strip()
    if env and os.path.isdir(env):
        base = env
    elif app_id:
        base = find_workspace(app_id) or os.path.join(ROOT, str(app_id))
    else:
        base = os.path.join(ROOT, "_noapp")
    d = os.path.join(base, sub) if sub else base
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def cache_dir() -> str:
    d = os.path.join(ROOT, "_cache")
    os.makedirs(d, exist_ok=True)
    return d


def job_path(filename: str) -> str:
    """一次性小任务的配置文件：_jobs/<时间戳>_<filename>，并行也不会撞名。"""
    _check("filename", filename)
    d = os.path.join(ROOT, "_jobs")
    os.makedirs(d, exist_ok=True)
    # Windows 上 time.time() 精度约 15ms，连调两次时间戳相同 —— 再拼 pid + 随机串才不撞名
    stamp = "%s-%d-%s" % (time.strftime("%Y%m%d-%H%M%S"), os.getpid(), uuid.uuid4().hex[:6])
    return os.path.join(d, "%s_%s" % (stamp, filename))


def resolve(skill: str, filename: str | None, app_id: str | None = None, sub: str | None = None) -> str:
    for label, part in (("skill name", skill), ("app id", app_id), ("sub dir", sub), ("filename", filename)):
        _check(label, part)
    if not skill:
        raise ValueError("invalid skill name: ''")
    if skill != DEFAULT_SKILL_NAME:          # 别的 skill 名：保持旧语义 <tmp>/<skill>/…
        d = os.path.join(tempfile.gettempdir(), skill, *[p for p in (app_id, sub) if p])
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, filename) if filename else d
    if app_id or sub:
        d = app_workdir(app_id, sub)
        return os.path.join(d, filename) if filename else d
    if filename:
        return job_path(filename)
    os.makedirs(ROOT, exist_ok=True)
    return ROOT


def self_test() -> int:
    """在隔离的临时根目录里把工作目录规则全跑一遍（不碰真实 jeecg-lowcode/、不联网）。全过返回 0。

    覆盖：开目录/撞秒、非 ASCII 拒收、绑定/回填/改绑拒绝、大小写与 8.3 短名、spec 在目录外、
    按 app_id 找回/多目录取最新、兜底 <app_id>/ 与 _noapp/、create=False 不建目录、环境变量覆盖、
    _jobs 防撞、_cache、resolve；以及另外两个 skill 里的副本（dashboard 的 _lowcode_workdir、
    miniflow 的 _APPS_CACHE）与本文件同一规则 —— 改规则时这两处要同步改。
    """
    import importlib.util
    import shutil

    global ROOT
    results = []

    def chk(name, cond, extra=""):
        results.append(bool(cond))
        print(("  ✓ " if cond else "  ✗ ") + name + ("" if cond else "  -> %s" % (extra,)))

    real_root, real_env = ROOT, os.environ.pop(ENV_WORKDIR, None)
    base = tempfile.mkdtemp(prefix="lowcode_selftest_")
    ROOT = os.path.join(base, DEFAULT_SKILL_NAME)
    os.makedirs(ROOT)
    same = lambda a, b: bool(a) and bool(b) and _norm(a) == _norm(b)
    try:
        a, b = new_workspace("crm"), new_workspace("crm")
        chk("--new 开目录并写 app.json（app_id 为空）", (_load(a) or {}).get("app_id", "x") is None)
        chk("同一秒开两个同名目录自动加 -2 后缀", a != b and os.path.basename(b).startswith(os.path.basename(a)), b)
        for bad in ("进销存", "../x", "a/b"):
            try:
                new_workspace(bad)
                chk("拒收非法简称 %r" % bad, False)
            except ValueError:
                chk("拒收非法简称 %r" % bad, True)

        spec = os.path.join(a, "sub", "app_spec.json")
        os.makedirs(os.path.dirname(spec))
        open(spec, "w").close()
        chk("spec 在工作目录子目录里也能绑定", same(bind_workspace(spec, "111", "CRM", 2), a))
        chk("app.json 回填 app_id / 名称 / 租户",
            (_load(a) or {}).get("app_id") == "111" and (_load(a) or {}).get("tenant_id") == "2")
        chk("同一 app_id 重复绑定不报错", same(bind_workspace(spec, "111"), a))
        try:
            bind_workspace(spec, "222")
            chk("已绑定目录拒绝改绑别的应用", False)
        except SystemExit:
            chk("已绑定目录拒绝改绑别的应用", True)
        if os.name == "nt":
            chk("路径大小写不同也能认出工作目录", same(bind_workspace(spec.upper(), "111"), a))
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(1024)
                ctypes.windll.kernel32.GetShortPathNameW(spec, buf, 1024)
                sp = buf.value
                chk("8.3 短路径也能认出工作目录", sp and same(bind_workspace(sp, "111"), a), sp)
            except Exception as exc:  # 取不到短名的文件系统：跳过不算失败
                print("  - 跳过 8.3 短路径（%s）" % exc)
        outside = os.path.join(base, "outside_spec.json")
        open(outside, "w").close()
        chk("spec 不在任何工作目录里 -> 不绑定", bind_workspace(outside, "333") is None)

        chk("按 app_id 找回工作目录", same(app_workdir("111", "build"), os.path.join(a, "build")))
        chk("没有工作目录的应用 -> 兜底 <app_id>/", same(app_workdir("999", "patch"), os.path.join(ROOT, "999", "patch")))
        chk("没有 app_id -> 兜底 _noapp/", same(app_workdir(None, "link"), os.path.join(ROOT, "_noapp", "link")))
        p0 = app_workdir("0", create=False)
        chk("create=False 只算路径、不建目录", not os.path.exists(p0), p0)
        time.sleep(1.1)
        c = new_workspace("crm")
        bind_workspace(c, "111")
        chk("同一 app_id 有多个工作目录时取最新", same(find_workspace("111"), c))

        env = os.path.join(base, "envdir")
        os.makedirs(env)
        os.environ[ENV_WORKDIR] = env
        chk("环境变量 %s 优先级最高" % ENV_WORKDIR, same(app_workdir("111", "x"), os.path.join(env, "x")))
        os.environ[ENV_WORKDIR] = os.path.join(base, "missing")
        chk("环境变量指向不存在的目录时忽略", same(app_workdir("111", "x"), os.path.join(c, "x")))
        os.environ.pop(ENV_WORKDIR, None)

        j1, j2 = job_path("job.json"), job_path("job.json")
        chk("_jobs 连续两次取名不重复", j1 != j2 and same(os.path.dirname(j1), os.path.join(ROOT, "_jobs")), (j1, j2))
        chk("_cache 目录", same(cache_dir(), os.path.join(ROOT, "_cache")))
        chk("resolve 无参数 -> 根目录", same(resolve(DEFAULT_SKILL_NAME, None), ROOT))
        chk("resolve --app-id --sub -f -> 工作目录内", same(resolve(DEFAULT_SKILL_NAME, "f.json", "111", "patch"),
                                                        os.path.join(c, "patch", "f.json")))

        # 另外两个 skill 里的副本：同目录布局（…/jeecg-lowcode-lowapp/scripts/ 的兄弟 skill）才能找到
        skills = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        copies = (("dashboard 的 _lowcode_workdir", os.path.join(skills, "jeecg-lowcode-dashboard", "references",
                                                                  "scripts", "build_dashboards.py")),
                  ("miniflow 的 _APPS_CACHE", os.path.join(skills, "jeecg-lowcode-miniflow", "scripts",
                                                          "timer_job_runner.py")))
        for label, path in copies:
            if not os.path.isfile(path):
                print("  - 跳过 %s（没找到 %s）" % (label, path))
                continue
            try:
                sys.path.insert(0, os.path.dirname(path))
                spec_ = importlib.util.spec_from_file_location("_lowcode_copy_%d" % len(results), path)
                mod = importlib.util.module_from_spec(spec_)
                spec_.loader.exec_module(mod)
                if hasattr(mod, "_lowcode_workdir"):
                    orig = mod.tempfile.gettempdir
                    mod.tempfile.gettempdir = lambda: base
                    try:
                        ok = all(same(mod._lowcode_workdir(x, "dash"), app_workdir(x, "dash", create=False))
                                 for x in ("111", "999"))
                    finally:
                        mod.tempfile.gettempdir = orig
                    chk(label + " 与本文件同一规则", ok)
                else:
                    want = os.path.join(real_root, "_cache", "miniflow_apps.json")
                    chk(label + " 落在 _cache/ 下", same(getattr(mod, "_APPS_CACHE", ""), want),
                        getattr(mod, "_APPS_CACHE", None))
            except Exception as exc:
                chk(label + " 可导入并比对", False, exc)
            finally:
                sys.path.remove(os.path.dirname(path))
    finally:
        ROOT = real_root
        if real_env is not None:
            os.environ[ENV_WORKDIR] = real_env
        shutil.rmtree(base, ignore_errors=True)
    ok = sum(results)
    print("%d/%d 通过" % (ok, len(results)))
    return 0 if ok == len(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="敲敲云 skill 临时目录（一次建应用一个工作目录）")
    parser.add_argument("-f", "--filename", default=None, help="文件名（裸名，仅 ASCII）")
    parser.add_argument("--skill", default=DEFAULT_SKILL_NAME, help=f"根目录名（默认 {DEFAULT_SKILL_NAME}）")
    parser.add_argument("--new", metavar="SLUG", default=None,
                        help="开一个工作目录 <SLUG>_<时间戳>/ 并打印路径（建应用第一步；SLUG=应用名的英文简称）")
    parser.add_argument("--app-id", default=None, help="应用 id：返回它的工作目录（没有则 jeecg-lowcode/<app_id>）")
    parser.add_argument("--sub", default=None, help="子目录（如 patch、link）")
    parser.add_argument("--self-test", action="store_true", help="隔离目录里自检全部规则（改本文件后必跑）")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.new is not None:
            path = new_workspace(args.new)
            if args.filename:
                _check("filename", args.filename)
                path = os.path.join(path, args.filename)
        else:
            path = resolve(args.skill, args.filename, args.app_id, args.sub)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
