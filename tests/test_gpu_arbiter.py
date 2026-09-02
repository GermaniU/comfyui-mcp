"""Tests del arbiter: el start se reintenta dentro de la ventana de wake."""

from comfyui_mcp import gpu_arbiter


async def test_start_se_reintenta_dentro_de_la_ventana(monkeypatch):
    monkeypatch.setattr(gpu_arbiter, "_START_FLOOR_S", 0)
    monkeypatch.setattr(gpu_arbiter, "_WAKE_POLL_S", 0)
    monkeypatch.setattr(gpu_arbiter, "_WAKE_TIMEOUT_S", 30)
    starts = []
    resets = []

    def fake_run(cmd, **kw):
        if "start" in cmd:
            starts.append(cmd)
        if "reset-failed" in cmd:
            resets.append(cmd)

    respuestas = iter([False, False, True])

    async def fake_reachable():
        return next(respuestas)

    monkeypatch.setattr(gpu_arbiter.subprocess, "run", fake_run)
    monkeypatch.setattr(gpu_arbiter.comfy_client, "reachable", fake_reachable)

    assert await gpu_arbiter.ensure_comfyui_running() is None
    assert len(starts) >= 2, "el start debe reintentarse dentro de la ventana"
    assert len(resets) >= 2, "cada intento debe despejar el rate-limit antes"


async def test_error_nombra_la_causa_cuando_no_despierta(monkeypatch):
    monkeypatch.setattr(gpu_arbiter, "_START_FLOOR_S", 5)
    monkeypatch.setattr(gpu_arbiter, "_WAKE_POLL_S", 0)
    monkeypatch.setattr(gpu_arbiter, "_WAKE_TIMEOUT_S", 0.2)

    async def nunca():
        return False

    monkeypatch.setattr(gpu_arbiter.subprocess, "run", lambda cmd, **kw: None)
    monkeypatch.setattr(gpu_arbiter.comfy_client, "reachable", nunca)

    err = await gpu_arbiter.ensure_comfyui_running()
    assert err is not None
    assert "speaches" in err and "VRAM" in err