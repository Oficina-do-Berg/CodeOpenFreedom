# -*- coding: utf-8 -*-
"""
Testes seguros do fluxo do CodeOpen.

Não rotaciona WARP, não abre o OpenCode e não apaga auth/chats.
"""

import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import Config, ConnectionManager, LogMonitor, OpenCodeManager, Orchestrator


class FakeConfig:
    def __init__(self, **values):
        self.values = {
            "settle_seconds": 0.2,
            "max_retries": 3,
            "retry_delay": 1,
            "auto_rotate": True,
            "auto_continue": True,
            "start_continue": True,
            "probe_enabled": False,
            "resume_auto": True,
            "resume_timeout": 30,
            "max_rotations_per_window": 5,
            "rotation_window_minutes": 30,
            "rotate_on_rate_limit": False,
        }
        self.values.update(values)

    def get(self, key, default=None):
        return self.values.get(key, default)


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def check(name, condition, detail=""):
    status = "OK " if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" - {detail}" if detail and not condition else ""))
    return bool(condition)


def test_classificacao():
    print("\n1. Classificação de linhas")
    monitor = LogMonitor(FakeConfig())
    monitor.start_utc = "2026-01-01T00:00:00"

    ok = True
    ok &= check(
        "level=INFO com 'usage limit' é ignorado",
        monitor.classify_line(
            'timestamp=2026-01-02T00:00:00.000Z level=INFO message="usage limit"'
        ) is None
    )
    ok &= check(
        "linha anterior ao início é ignorada",
        monitor.classify_line(
            'timestamp=2025-12-31T23:59:59.000Z level=ERROR message="Free usage limit reached"'
        ) is None
    )
    ok &= check(
        "free usage limit vira rotate",
        monitor.classify_line(
            'timestamp=2026-01-02T00:00:00.000Z level=ERROR message="Free usage limit reached"'
        ) == "rotate"
    )
    ok &= check(
        "rate limit vira ask",
        monitor.classify_line(
            'timestamp=2026-01-02T00:00:00.000Z level=ERROR message="rate limit exceeded"'
        ) == "ask"
    )
    ok &= check(
        "compactação vira noop",
        monitor.classify_line(
            'timestamp=2026-01-02T00:00:00.000Z level=ERROR message="compaction failed"'
        ) == "noop"
    )
    return bool(ok)


def test_monitor_so_linhas_novas():
    print("\n2. Monitor ignora o passado e pega só linha nova")

    with tempfile.TemporaryDirectory() as tmp:
        log_file = Path(tmp) / "opencode.log"
        log_file.write_text(
            'timestamp=2025-01-01T00:00:00.000Z level=ERROR message="Free usage limit reached"\n',
            encoding="utf-8",
        )

        hits = []
        monitor = LogMonitor(FakeConfig(), on_limit_callback=lambda: hits.append(time.time()),
                             log_path=str(log_file))
        monitor.start()
        time.sleep(1.2)

        old_ok = check("erro antigo não dispara", not hits)

        # linha antiga escrita depois do start também deve ser ignorada pelo timestamp
        with open(log_file, "a", encoding="utf-8") as f:
            f.write('timestamp=2020-01-01T00:00:00.000Z level=ERROR message="Free usage limit reached"\n')
        time.sleep(1.2)
        old_ok &= check("linha com timestamp antigo não dispara", not hits)

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(
                f'timestamp={utc_now()}.000Z level=ERROR '
                f'message="Free usage limit reached." cause="AI.Error"\n'
            )

        deadline = time.time() + 8
        while time.time() < deadline and not hits:
            time.sleep(0.2)

        new_ok = check("linha nova dispara o desbloqueio", bool(hits))
        monitor.stop()
        return bool(old_ok and new_ok)


def test_auth_e_ambiente():
    print("\n3. Auth correto e ambiente de proxy")
    manager = OpenCodeManager(FakeConfig())

    auth = manager.get_auth_file()
    ok = check("auth aponta para auth.json", auth.name == "auth.json", str(auth))
    ok &= check(
        "auth fica em .local/share/opencode",
        ".local" in str(auth) and "share" in str(auth),
        str(auth),
    )

    env = manager._build_env("http://127.0.0.1:40000")
    ok &= check("HTTPS_PROXY configurado", env.get("HTTPS_PROXY") == "http://127.0.0.1:40000")
    ok &= check("HTTP_PROXY configurado", env.get("HTTP_PROXY") == "http://127.0.0.1:40000")
    return bool(ok)


def test_pid_ignora_servico():
    print("\n4. Processo: TUI != serviço de background")
    import core.opencode as ocmod

    class FakeProc:
        def __init__(self, pid, name, cmdline):
            self.info = {"pid": pid, "name": name, "cmdline": cmdline}

    original = ocmod.psutil.process_iter
    ocmod.psutil.process_iter = lambda attrs=None: [
        FakeProc(24508, "opencode.exe", [
            r"C:\Users\berg\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe",
            "serve", "--service",
        ]),
        FakeProc(12956, "opencode.exe", [
            r"C:\Users\berg\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe",
            "serve", "--stdio", "--port", "0",
        ]),
        FakeProc(16976, "opencode.exe", [
            r"C:\Users\berg\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe",
            "run", "--auto", "--standalone", "-c", "continue",
        ]),
        FakeProc(10304, "opencode.exe", [
            r"C:\Users\berg\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe",
            "--standalone",
        ]),
    ]

    try:
        manager = OpenCodeManager(FakeConfig())
        pid = manager.find_running_pid()
        ok = check("serviço é ignorado e o TUI é retornado", pid == 10304, f"pid={pid}")

        service_pid = manager.find_service_pid()
        ok &= check(
            "serviço de background é encontrado",
            service_pid == 24508,
            f"pid={service_pid}",
        )
        ok &= check(
            "serve --stdio da sessão não é tratado como serviço",
            service_pid != 12956,
            f"pid={service_pid}",
        )
    finally:
        ocmod.psutil.process_iter = original

    return bool(ok)


def test_ip_key():
    print("\n5. Comparação de IP (IPv4 e IPv6 /64)")
    key = ConnectionManager._ip_key
    ok = check("IPv4 igual", key("1.2.3.4") == key("1.2.3.4"))
    ok &= check("IPv4 diferente", key("1.2.3.4") != key("1.2.3.5"))
    ok &= check(
        "IPv6 no mesmo /64 é igual",
        key("2a09:bac5:593:297d::422:53") == key("2a09:bac5:593:297d:0:0:0:1"),
    )
    ok &= check(
        "IPv6 em /64 diferente não é igual",
        key("2a09:bac5:593:297d::1") != key("2a09:bac5:593:297e::1"),
    )
    return bool(ok)


def test_anti_loop():
    print("\n6. Anti-loop de rotações")
    config = FakeConfig(max_rotations_per_window=5, rotation_window_minutes=30)
    monitor = LogMonitor(config)
    orchestrator = Orchestrator(None, None, None, monitor, config)

    results = [orchestrator._rotation_allowed() for _ in range(6)]
    ok = check("5 rotações permitidas", all(results[:5]), str(results))
    ok &= check("a 6ª é bloqueada", results[5] is False, str(results))
    return bool(ok)


def test_comandos():
    print("\n7. Comandos: resume, probe e abertura do TUI")
    import subprocess as sp
    from unittest.mock import patch

    manager = OpenCodeManager(FakeConfig(probe_enabled=True))
    manager.opencode_path = r"C:\fake\opencode.cmd"
    manager.working_dir = tempfile.gettempdir()
    manager.supports_standalone = lambda: True

    captured = []

    def fake_run(args, **kwargs):
        captured.append(list(args))
        return sp.CompletedProcess(["opencode"] + list(args), 0, "", "")

    manager._run_cli = fake_run

    status, _ = manager.resume("http://127.0.0.1:40000", cwd=tempfile.gettempdir())
    resume_args = captured[-1]
    ok = check(
        "resume usa run --auto --standalone -c",
        resume_args[:4] == ["run", "--auto", "--standalone", "-c"],
        str(resume_args),
    )
    ok &= check("resume manda a mensagem", resume_args[-1] == "continue", str(resume_args))

    manager.probe("http://127.0.0.1:40000", cwd=tempfile.gettempdir())
    probe_args = captured[-1]
    ok &= check("probe usa --standalone", "--standalone" in probe_args, str(probe_args))
    ok &= check("probe usa --auto", "--auto" in probe_args, str(probe_args))
    ok &= check("probe tem mensagem curta", probe_args[-1] == "reply with just: ok", str(probe_args))

    class FakeProcess:
        pid = 424242

        def poll(self):
            return None

    manager.is_running = lambda: False
    with patch("core.opencode.subprocess.Popen", return_value=FakeProcess()) as popen, \
         patch("core.opencode.time.sleep", return_value=None):
        started = manager.start(
            proxy_url="http://127.0.0.1:40000",
            continue_session=True,
        )

    cmd = popen.call_args[0][0]
    ok &= check(
        "TUI abre com --standalone --continue",
        started and cmd == [manager.opencode_path, "--standalone", "--continue"],
        str(cmd),
    )
    return bool(ok)


def main():
    print("=" * 70)
    print(" TESTES SEGUROS - CODEOPEN")
    print("=" * 70)

    tests = [
        test_classificacao,
        test_monitor_so_linhas_novas,
        test_auth_e_ambiente,
        test_pid_ignora_servico,
        test_ip_key,
        test_anti_loop,
        test_comandos,
    ]

    results = []
    for test in tests:
        try:
            results.append(bool(test()))
        except Exception as e:
            import traceback
            print(f"  [FAIL] {test.__name__}: {e}")
            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 70)
    passed = sum(1 for r in results if r)
    print(f" RESULTADO: {passed}/{len(results)} grupos passaram")
    print("=" * 70)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
