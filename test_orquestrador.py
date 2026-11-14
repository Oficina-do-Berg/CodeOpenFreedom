# -*- coding: utf-8 -*-
"""
Teste do fluxo de desbloqueio com componentes falsos.

Não toca em WARP, OpenCode, auth ou chats.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import Orchestrator


class FakeConfig:
    def __init__(self, **values):
        self.values = {
            "max_retries": 3,
            "retry_delay": 0,
            "auto_rotate": True,
            "auto_continue": True,
            "probe_enabled": True,
            "max_rotations_per_window": 5,
            "rotation_window_minutes": 30,
            "rotate_on_rate_limit": False,
        }
        self.values.update(values)

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeConnection:
    def __init__(self):
        self.current_ip = "1.1.1.1"
        self.proxy_url = "http://127.0.0.1:40000"
        self.current_method = "WARP"
        self.rotations = 0

    def connect(self, method):
        return True, "conectado"

    def rotate_warp_ip(self, max_attempts=1):
        self.rotations += 1
        self.current_ip = f"1.1.1.{self.rotations + 1}"
        return True, f"IP {self.current_ip}"

    def get_status(self):
        return {
            "method": self.current_method,
            "ip": self.current_ip,
            "proxy_url": self.proxy_url,
            "connected": True,
        }


class FakeRotator:
    def __init__(self, connection):
        self.connection = connection
        self.rotation_count = 0

    def rotate(self, max_retries=None, deep_reset=False):
        ok, _ = self.connection.rotate_warp_ip()
        if ok:
            self.rotation_count += 1
        return ok


class FakeOpenCode:
    def __init__(self, probe_results=None, resume_results=None):
        self.probe_results = list(probe_results or [])
        self.resume_results = list(resume_results or [])
        self.stopped = 0
        self.started = 0
        self.started_with = []
        self.probe_calls = 0
        self.resume_calls = 0

    def stop(self):
        self.stopped += 1
        return True

    def is_running(self):
        return True

    def is_service_running(self):
        return False

    def probe(self, proxy_url, cwd=None, model=None):
        self.probe_calls += 1
        return self.probe_results.pop(0) if self.probe_results else ("ok", "")

    def resume(self, proxy_url, cwd=None):
        self.resume_calls += 1
        return self.resume_results.pop(0) if self.resume_results else ("ok", "")

    def start(self, proxy_url=None, continue_session=False):
        self.started += 1
        self.started_with.append((proxy_url, continue_session))
        return True


class FakeMonitor:
    def __init__(self):
        self.on_limit = None
        self.on_ask = None
        self.started = 0

    def start(self):
        self.started += 1

    def stop(self):
        pass

    def is_monitoring(self):
        return False


def check(name, condition, detail=""):
    status = "OK " if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" - {detail}" if detail and not condition else ""))
    return bool(condition)


def build(probe_results=None, resume_results=None, **config):
    cfg = FakeConfig(**config)
    connection = FakeConnection()
    rotator = FakeRotator(connection)
    opencode = FakeOpenCode(probe_results, resume_results)
    monitor = FakeMonitor()
    orchestrator = Orchestrator(connection, opencode, rotator, monitor, cfg)
    return orchestrator, opencode, rotator, monitor, connection


def run(orchestrator):
    with patch("core.orchestrator.time.sleep", return_value=None):
        orchestrator.handle_limit_detected()


def test_normal():
    print("\n1. Fluxo normal: rotaciona → probe ok → resume ok → reabre")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("ok", "")],
        resume_results=[("ok", "")],
    )
    run(orchestrator)

    ok = check("parou o TUI", opencode.stopped == 1)
    ok &= check("rotacionou uma vez", rotator.rotation_count == 1)
    ok &= check("fez probe", opencode.probe_calls == 1)
    ok &= check("retomou a conversa", opencode.resume_calls == 1)
    ok &= check("reabriu na conversa", opencode.started_with == [
        (connection.proxy_url, True)
    ], str(opencode.started_with))
    ok &= check("monitor religado", monitor.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_rota_queimada():
    print("\n2. Primeira rota ainda limitada: tenta a segunda")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("burned", "usage limit"), ("ok", "")],
        resume_results=[("ok", "")],
    )
    run(orchestrator)

    ok = check("rotacionou duas vezes", rotator.rotation_count == 2)
    ok &= check("fez probe duas vezes", opencode.probe_calls == 2)
    ok &= check("reabriu uma vez", opencode.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_resume_limitado():
    print("\n3. Resume bate no limite: rotaciona de novo e retoma")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("ok", ""), ("ok", "")],
        resume_results=[("limit", "usage limit"), ("ok", "")],
    )
    run(orchestrator)

    ok = check("rotacionou duas vezes", rotator.rotation_count == 2)
    ok &= check("retomou duas vezes", opencode.resume_calls == 2)
    ok &= check("reabriu uma vez", opencode.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_sem_sessao():
    print("\n4. Sem conversa anterior: reabre sem girar de novo")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("ok", "")],
        resume_results=[("no_session", "")],
    )
    run(orchestrator)

    ok = check("rotacionou uma vez", rotator.rotation_count == 1)
    ok &= check("reabriu uma vez", opencode.started == 1)
    ok &= check("monitor religado", monitor.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_todas_falham():
    print("\n5. Todas as rotas limitadas: para e reabre sem monitor")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("burned", "limit")] * 3,
        resume_results=[],
        max_retries=3,
    )
    run(orchestrator)

    ok = check("tentou 3 rotações", rotator.rotation_count == 3)
    ok &= check("não retomou", opencode.resume_calls == 0)
    ok &= check("reabriu para o usuário", opencode.started == 1)
    ok &= check("não religou o monitor", monitor.started == 0)
    ok &= check("resultado de falha", orchestrator.last_result == "falha no desbloqueio")
    return bool(ok)


def test_anti_loop():
    print("\n6. Anti-loop: segunda sequência é bloqueada")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("ok", ""), ("ok", "")],
        resume_results=[("ok", ""), ("ok", "")],
        max_rotations_per_window=1,
    )
    run(orchestrator)
    first_ok = orchestrator.last_result == "desbloqueado"

    run(orchestrator)
    second_blocked = orchestrator.last_result == "limite de rotações atingido"

    ok = check("primeira passou", first_ok)
    ok &= check("segunda bloqueada", second_blocked)
    ok &= check("não parou o TUI de novo", opencode.stopped == 1, str(opencode.stopped))
    return bool(ok)


def test_retomada_aviso_nao_descarta_rota():
    print("\n7. Retomada com retorno não-padrão sem limite: preserva rota boa")
    cfg = FakeConfig()
    conn = FakeConnection()
    rot = FakeRotator(conn)
    # resume retorna 'error' sem mensagem de limite (ex.: sem mensagem pendente)
    oc = FakeOpenCode(resume_results=[("error", "no message was pending")])
    mon = FakeMonitor()
    orc = Orchestrator(conn, oc, rot, mon, cfg)

    orc.handle_limit_detected()

    ok = check("rotacionou apenas uma vez", rot.rotation_count == 1, str(rot.rotation_count))
    ok &= check("reabriu com sucesso", oc.started == 1, str(oc.started))
    ok &= check("resultado desbloqueado", orc.last_result == "desbloqueado", orc.last_result)
    return bool(ok)


def test_concorrencia_bloqueia_start():
    print("\n8. Concorrência: start_full_flow bloqueado durante desbloqueio")
    cfg = FakeConfig()
    conn = FakeConnection()
    rot = FakeRotator(conn)
    oc = FakeOpenCode()
    mon = FakeMonitor()
    orc = Orchestrator(conn, oc, rot, mon, cfg)

    orc.is_unlocking = True
    bloqueado = not orc.start_full_flow()
    orc.is_unlocking = False

    ok = check("start_full_flow recusado enquanto is_unlocking=True", bloqueado)
    return bool(ok)


def main():
    print("=" * 70)
    print(" TESTE DO ORQUESTRADOR (COMPONENTES FALSOS)")
    print("=" * 70)

    tests = [
        test_normal,
        test_rota_queimada,
        test_resume_limitado,
        test_sem_sessao,
        test_todas_falham,
        test_anti_loop,
        test_retomada_aviso_nao_descarta_rota,
        test_concorrencia_bloqueia_start,
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
    print(f" RESULTADO: {passed}/{len(results)} cenários passaram")
    print("=" * 70)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
