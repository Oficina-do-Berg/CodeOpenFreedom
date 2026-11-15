# -*- coding: utf-8 -*-
"""
Teste do fluxo de desbloqueio com componentes falsos.

Não toca em WARP, OpenCode, auth ou chats.

A lógica testada é a do main:
1. troca o IP e testa a rota com o MESMO modelo da conversa;
2. se a rota ainda está limitada, gira de novo (até hunt_max);
3. quando o probe passa, retoma a conversa;
4. se a caçada falhar, tenta outro modelo livre (LIMIT_ACTION=provider).
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
            "probe_model": "",
            "probe_broken_max": 2,
            "hunt_max": 10,
            "limit_rot_max": 50,
            "rotate_on_rate_limit": False,
            "max_model_switches": 4,
            "model_candidates": ["opencode/model-a", "opencode/model-b", "opencode/model-c"],
            "last_good_model": "",
            "model_switch_fallback": True,
        }
        self.values.update(values)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


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
    def __init__(self, probe_results=None, resume_results=None, session_model="opencode/model-a"):
        self.probe_results = list(probe_results or [])
        self.resume_results = list(resume_results or [])
        self.session_model = session_model
        self.stopped = 0
        self.started = 0
        self.started_with = []
        self.models_fixed = []
        self.models_fixed_tui = []
        self.probe_calls = 0
        self.resume_calls = 0
        self.probe_models = []
        self.resume_calls_detail = []

    def stop(self):
        self.stopped += 1
        return True

    def is_running(self):
        return True

    def is_service_running(self):
        return False

    def latest_session(self, cwd=None):
        return "ses_test", self.session_model, cwd

    def model_last_used(self):
        return {}

    def list_free_models(self):
        return []

    def retry_after_ms(self, text):
        import re
        match = re.search(r'"retryAfterMs"\s*:\s*(\d+)', text or "")
        return int(match.group(1)) if match else 0

    def probe(self, proxy_url, cwd=None, model=None):
        self.probe_calls += 1
        self.probe_models.append(model)
        return self.probe_results.pop(0) if self.probe_results else ("ok", "")

    def resume(self, proxy_url, cwd=None, model=None, session_id=None):
        self.resume_calls += 1
        self.resume_calls_detail.append((model, session_id))
        return self.resume_results.pop(0) if self.resume_results else ("ok", "")

    def set_session_model(self, session_id, model):
        self.models_fixed.append((session_id, model))
        return True

    def set_tui_model(self, model):
        self.models_fixed_tui.append(model)
        return True

    def start(self, folder=None, proxy_url=None, continue_session=False, session_id=None):
        self.started += 1
        self.started_with.append((proxy_url, continue_session, session_id))
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
    print("\n1. Rota nova aceita o modelo da conversa: retoma")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("ok", "")],
        resume_results=[("ok", "")],
    )
    run(orchestrator)

    ok = check("parou o TUI", opencode.stopped == 1)
    ok &= check("trocou o IP uma vez (lógica do main)", rotator.rotation_count == 1,
                str(rotator.rotation_count))
    ok &= check("testou o modelo da conversa",
                opencode.probe_models == ["opencode/model-a"], str(opencode.probe_models))
    ok &= check("retomou a mesma sessão com o modelo testado",
                opencode.resume_calls_detail == [("opencode/model-a", "ses_test")],
                str(opencode.resume_calls_detail))
    ok &= check("reabriu na conversa fixada pelo id", opencode.started_with == [
        (connection.proxy_url, True, "ses_test")
    ], str(opencode.started_with))
    ok &= check("não trocou o modelo (é o da conversa)", opencode.models_fixed == [],
                str(opencode.models_fixed))
    ok &= check("monitor religado", monitor.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_rota_queimada():
    print("\n2. Rota limitada: gira de novo até o probe passar")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[
            ("burned", '{"retryAfterMs":3600000}'),
            ("burned", '{"retryAfterMs":3600000}'),
            ("ok", ""),
        ],
        resume_results=[("ok", "")],
        hunt_max=10,
    )
    run(orchestrator)

    ok = check("girou 3 vezes", rotator.rotation_count == 3, str(rotator.rotation_count))
    ok &= check("testou o mesmo modelo nas 3 rotas",
                opencode.probe_models == ["opencode/model-a"] * 3,
                str(opencode.probe_models))
    ok &= check("retomou só depois do probe passar",
                opencode.resume_calls_detail == [("opencode/model-a", "ses_test")],
                str(opencode.resume_calls_detail))
    ok &= check("reabriu uma vez", opencode.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_resume_limitado():
    print("\n3. Probe passa mas a retomada bate no limite: gira de novo")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("ok", ""), ("ok", "")],
        resume_results=[("limit", '{"retryAfterMs":3600000}'), ("ok", "")],
    )
    run(orchestrator)

    ok = check("girou 2 vezes", rotator.rotation_count == 2, str(rotator.rotation_count))
    ok &= check("retomou 2 vezes", opencode.resume_calls == 2, str(opencode.resume_calls))
    ok &= check("reabriu uma vez", opencode.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_sem_sessao():
    print("\n4. Sem conversa anterior: reabre")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("ok", "")],
        resume_results=[("no_session", "")],
    )
    run(orchestrator)

    ok = check("girou uma vez", rotator.rotation_count == 1, str(rotator.rotation_count))
    ok &= check("reabriu uma vez", opencode.started == 1)
    ok &= check("monitor religado", monitor.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_cacada_esgotada():
    print("\n5. Caçada esgotada e fallback desligado: desiste e reabre")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("burned", '{"retryAfterMs":7200000}')] * 3,
        resume_results=[],
        hunt_max=3,
        model_switch_fallback=False,
    )
    run(orchestrator)

    ok = check("girou hunt_max vezes", rotator.rotation_count == 3, str(rotator.rotation_count))
    ok &= check("testou o modelo da conversa 3 vezes", opencode.probe_calls == 3,
                str(opencode.probe_calls))
    ok &= check("não retomou", opencode.resume_calls == 0)
    ok &= check("reabriu para o usuário", opencode.started == 1)
    ok &= check("não religou o monitor", monitor.started == 0)
    ok &= check("resultado de falha", orchestrator.last_result == "falha no desbloqueio")
    return bool(ok)


def test_fallback_modelo():
    print("\n6. Caçada esgotada: fallback troca de modelo na rota atual")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[
            ("burned", ""), ("burned", ""),      # caçada no model-a
            ("ok", ""),                          # fallback no model-b
        ],
        resume_results=[("ok", "")],
        hunt_max=2,
    )
    run(orchestrator)

    ok = check("girou hunt_max vezes", rotator.rotation_count == 2, str(rotator.rotation_count))
    ok &= check("testou model-a e depois model-b",
                opencode.probe_models ==
                ["opencode/model-a", "opencode/model-a", "opencode/model-b"],
                str(opencode.probe_models))
    ok &= check("retomou com model-b",
                opencode.resume_calls_detail == [("opencode/model-b", "ses_test")],
                str(opencode.resume_calls_detail))
    ok &= check("fixou o model-b na conversa (o TUI reabre com ele)",
                opencode.models_fixed == [("ses_test", "opencode/model-b")],
                str(opencode.models_fixed))
    ok &= check("model-b na frente dos recentes do TUI",
                opencode.models_fixed_tui == ["opencode/model-b"],
                str(opencode.models_fixed_tui))
    ok &= check("reabriu uma vez", opencode.started == 1)
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_probe_quebrado():
    print("\n7. Probe quebrado: segue sem probe, como o .bat com PROBE=0")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("broken", "sem pong"), ("broken", "sem pong")],
        resume_results=[("ok", "")],
        hunt_max=3,
        probe_broken_max=2,
    )
    run(orchestrator)

    ok = check("girou 3 vezes", rotator.rotation_count == 3, str(rotator.rotation_count))
    ok &= check("parou de testar após 2 probes quebrados", opencode.probe_calls == 2,
                str(opencode.probe_calls))
    ok &= check("retomou sem probe na última rota", opencode.resume_calls == 1,
                str(opencode.resume_calls))
    ok &= check("resultado desbloqueado", orchestrator.last_result == "desbloqueado")
    return bool(ok)


def test_anti_loop():
    print("\n8. Anti-loop do main: desbloqueios seguidos sem resolver pausam o automático")
    orchestrator, opencode, rotator, monitor, connection = build(
        probe_results=[("burned", "")] * 6,
        resume_results=[],
        hunt_max=1,
        model_switch_fallback=False,
        limit_rot_max=2,
    )
    run(orchestrator)
    run(orchestrator)
    falhas = check("dois desbloqueios seguidos rodam", opencode.stopped == 2, str(opencode.stopped))
    run(orchestrator)
    bloqueado = check(
        "o 3º seguido é bloqueado (limit_rot_max=2)",
        opencode.stopped == 2 and orchestrator.last_result == "limite de desbloqueios seguidos",
        orchestrator.last_result,
    )
    orchestrator.reset_streak()
    run(orchestrator)
    liberado = check("ação manual libera o automático", opencode.stopped == 3, str(opencode.stopped))
    return bool(falhas and bloqueado and liberado)


def test_retomada_aviso_nao_descarta_rota():
    print("\n9. Retomada com retorno não-padrão sem limite: preserva rota boa")
    cfg = FakeConfig()
    conn = FakeConnection()
    rot = FakeRotator(conn)
    oc = FakeOpenCode(resume_results=[("error", "no message was pending")])
    mon = FakeMonitor()
    orc = Orchestrator(conn, oc, rot, mon, cfg)

    orc.handle_limit_detected()

    ok = check("girou apenas uma vez", rot.rotation_count == 1, str(rot.rotation_count))
    ok &= check("reabriu com sucesso", oc.started == 1, str(oc.started))
    ok &= check("resultado desbloqueado", orc.last_result == "desbloqueado", orc.last_result)
    return bool(ok)


def test_concorrencia_bloqueia_start():
    print("\n10. Concorrência: start_full_flow bloqueado durante desbloqueio")
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


def test_nova_conversa():
    print("\n11. NOVA CONVERSA: gira o IP e abre sessão nova (opção 1 do main)")
    orchestrator, opencode, rotator, monitor, connection = build()

    ok = check("fluxo iniciou", orchestrator.start_full_flow(fresh=True))
    ok &= check("girou o IP antes de abrir", rotator.rotation_count == 1,
                str(rotator.rotation_count))
    ok &= check("abriu sem --continue e sem fixar sessão",
                opencode.started_with == [(connection.proxy_url, False, None)],
                str(opencode.started_with))
    ok &= check("monitor ligado", monitor.started == 1, str(monitor.started))
    ok &= check("streak zerado", orchestrator._quota_streak == 0,
                str(orchestrator._quota_streak))
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
        test_cacada_esgotada,
        test_fallback_modelo,
        test_probe_quebrado,
        test_anti_loop,
        test_retomada_aviso_nao_descarta_rota,
        test_concorrencia_bloqueia_start,
        test_nova_conversa,
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
