#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Irrigazione dashboard server (port 1977).

La dashboard usa il component e_dry per zone/programmi e usa e-SunMind
come sorgente meteo unica tramite /api/device_weather.
"""

import os
import json
import time
import requests
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import sys
import subprocess
import traceback
import threading

app = Flask(__name__)
VERSION = "10.5.15"
print(f"[e-Dry Irrigazione] Starting dashboard v{VERSION}")

START_TS = time.time()

HERE = Path(__file__).resolve().parent
INDEX_HTML = HERE / "index.html"
MANUAL_HTML = HERE / "manuale.html"

# cache ultimo stato zone per risposte vuote/fallite (anti-flicker)
LAST_STATE = {"zones": None, "active_zone": None}
LAST_STATE_TS = 0
LAST_STATE_DIRTY = False
LAST_STATE_LOG_TS = 0
WS_THREAD_STARTED = False
QUICK_SEQUENCE_LOCK = threading.Lock()
QUICK_SEQUENCE_CANCEL = threading.Event()
QUICK_SEQUENCE_SKIP = threading.Event()
QUICK_SEQUENCE_THREAD = None
QUICK_SEQUENCE_ID = 0
QUICK_SEQUENCE_STATE = {
    "active": False,
    "sequence_id": None,
    "zones": [],
    "minutes": None,
    "index": None,
    "current_zone_id": None,
    "current_started_at": None,
    "current_end_at": None,
    "next_zone_id": None,
    "status": "idle",
}

HA_BASE = os.environ.get("HA_BASE", "http://supervisor/core")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")

HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "Content-Type": "application/json"}

EVENT_LOG_ENTITY = os.environ.get("EVENT_LOG_ENTITY", "sensor.e_dry_event_log")
DEFAULT_ESUNMIND_API_URL = os.environ.get("E_SUNMIND_API_URL", "http://192.168.3.24:1980/api/weather/irrigation")


def read_options():
    try:
        with open("/data/options.json", "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _require_token():
    if not SUPERVISOR_TOKEN:
        return False, (jsonify({"error": "missing_supervisor_token", "detail": "SUPERVISOR_TOKEN non presente nell'addon"}), 500)
    return True, None


def _require_admin_settings(data=None):
    opts = read_options()
    expected = str(opts.get("admin_settings_password") or "").strip()
    if not expected:
        return False, (jsonify({
            "version": VERSION,
            "error": "admin_password_not_configured",
            "detail": "Configura admin_settings_password nelle opzioni dell'add-on per usare le tarature meteo protette.",
        }), 403)
    provided = (
        request.headers.get("X-Admin-Password")
        or request.args.get("admin_password")
        or ((data or {}).get("admin_password") if isinstance(data, dict) else None)
        or ""
    )
    if str(provided) != expected:
        return False, (jsonify({"version": VERSION, "error": "admin_password_invalid"}), 403)
    return True, None


def _start_ws_listener():
    """Background WS listener to mark cache dirty on state changes."""
    global WS_THREAD_STARTED
    if WS_THREAD_STARTED or not SUPERVISOR_TOKEN:
        return
    WS_THREAD_STARTED = True

    def _loop():
        import json as _json
        while True:
            try:
                try:
                    from websocket import create_connection
                except Exception:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    from websocket import create_connection

                ws_url = HA_BASE
                if HA_BASE.startswith("http://"):
                    ws_url = HA_BASE.replace("http://", "ws://")
                elif HA_BASE.startswith("https://"):
                    ws_url = HA_BASE.replace("https://", "wss://")
                if not ws_url.endswith("/api/websocket"):
                    ws_url = ws_url.rstrip("/") + "/api/websocket"

                ws = create_connection(ws_url, timeout=20)
                ws.send(_json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                auth_resp = _json.loads(ws.recv())
                if auth_resp.get("type") != "auth_ok":
                    try:
                        ws.close()
                    except Exception:
                        pass
                    time.sleep(5)
                    continue

                ws.send(_json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"}))
                while True:
                    msg = ws.recv()
                    if not msg:
                        break
                    try:
                        data = _json.loads(msg)
                        if data.get("type") == "event":
                            global LAST_STATE_DIRTY
                            LAST_STATE_DIRTY = True
                    except Exception:
                        continue
            except Exception:
                time.sleep(5)
                continue

    threading.Thread(target=_loop, daemon=True).start()

# start websocket listener at import time (best-effort)
_start_ws_listener()


@app.route("/")
@app.route("/index.html")
def index_page():
    if not INDEX_HTML.exists():
        return jsonify({
        "version": VERSION,"error": "index_missing", "detail": str(INDEX_HTML)}), 500
    return send_file(str(INDEX_HTML), mimetype="text/html; charset=utf-8")

@app.route("/manuale")
@app.route("/manuale.html")
def manual_page():
    if not MANUAL_HTML.exists():
        return jsonify({"version": VERSION, "error": "manual_missing", "detail": str(MANUAL_HTML)}), 500
    return send_file(str(MANUAL_HTML), mimetype="text/html; charset=utf-8")

@app.route("/e-dry.png")
def logo_png():
    logo2 = HERE / "e-dry2.png"
    if logo2.exists():
        return send_file(str(logo2))
    logo = HERE / "e-dry.png"
    if logo.exists():
        return send_file(str(logo))
    return ("", 404)

@app.route("/e-dry2.png")
def logo_png_v2():
    logo2 = HERE / "e-dry2.png"
    if logo2.exists():
        return send_file(str(logo2))
    return ("", 404)

@app.route("/e-konex-label.png")
def ekonex_label_png():
    logo = HERE / "e-konex-label.png"
    if logo.exists():
        return send_file(str(logo), mimetype="image/png")
    return ("", 404)

@app.route("/sfondo.png")
def background_png():
    bg = HERE / "sfondo.png"
    if bg.exists():
        return send_file(str(bg))
    return ("", 404)


@app.route("/stats")
def stats():
    return jsonify({
        "version": VERSION,"ok": True, "uptime_sec": int(time.time() - START_TS)})


def ha_get_states_all():
    """Return list of all states from HA (list of dicts)"""
    ok, _ = _require_token()
    if not ok:
        raise RuntimeError("missing token")
    r = requests.get(f"{HA_BASE}/api/states", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def ha_get_state(entity_id: str):
    ok, _ = _require_token()
    if not ok:
        raise RuntimeError("missing token")
    r = requests.get(f"{HA_BASE}/api/states/{entity_id}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def ha_get_entity_registry_list():
    ok, _ = _require_token()
    if not ok:
        raise RuntimeError("missing token")
    r = requests.get(f"{HA_BASE}/api/config/entity_registry/list", headers=HEADERS, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"entity_registry_list failed: {r.status_code} {r.text[:400]}")
    return r.json()


def resolve_entities_by_config_entry_registry(config_entry):
    """Resolve entities bound to a config_entry via entity registry (more robust than template)."""
    if not config_entry:
        return []
    try:
        reg = ha_get_entity_registry_list() or []
    except Exception:
        return []

    entity_ids = []
    ce_str = str(config_entry)
    for it in reg:
        try:
            eid = it.get('entity_id')
            if not eid:
                continue
            ce = it.get('config_entry_id')
            if ce is None:
                continue
            if isinstance(ce, (list, tuple)):
                if ce_str not in [str(x) for x in ce]:
                    continue
            else:
                if str(ce) != ce_str:
                    continue
            entity_ids.append(eid)
        except Exception:
            continue

    out = []
    for eid in entity_ids:
        try:
            st = ha_get_state(eid)
            if st:
                out.append(st)
        except Exception:
            continue
    return out


def ha_call_service(domain, service, payload):
    ok, _ = _require_token()
    if not ok:
        raise RuntimeError("missing token")
    r = requests.post(f"{HA_BASE}/api/services/{domain}/{service}", headers=HEADERS, json=payload, timeout=20)
    r.raise_for_status()
    return r.json() if r.text else {"ok": True}


def resolve_entities_by_config_entry(config_entry):
    """Use HA template API to collect entity_ids that belong to config_entry."""
    safe_ce = str(config_entry).replace("'", "\\'")
    template = (
        "{% set out = namespace(items=[]) %}\n"
        "{% for s in states %}\n"
        "  {% set ce = config_entry_id(s.entity_id) %}\n"
        "  {% if ce == '" + safe_ce + "' %}\n"
        "    {% set out.items = out.items + [ { 'entity_id': s.entity_id, 'state': s.state, 'attributes': s.attributes } ] %}\n"
        "  {% elif (ce is iterable) and (ce is not string) and ('" + safe_ce + "' in ce) %}\n"
        "    {% set out.items = out.items + [ { 'entity_id': s.entity_id, 'state': s.state, 'attributes': s.attributes } ] %}\n"
        "  {% endif %}\n"
        "{% endfor %}\n"
        "{{ out.items | tojson }}\n"
    )
    r = requests.post(f"{HA_BASE}/api/template", headers=HEADERS, json={"template": template}, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"template failed: {r.status_code} {r.text[:200]}")
    try:
        return json.loads(r.text)
    except Exception:
        return []


# -------------------- e_dry / config-entry discovery helpers --------------------
import re

_ZONE_PATTERNS = [
    re.compile(r"(?:\bzona\b|\bzone\b)\s*([0-9]{1,2})", re.I),
    re.compile(r"(?:^|[_\-.])z(?:ona)?_?([0-9]{1,2})(?:$|[_\-.])", re.I),
    re.compile(r"(?:^|[_\-.])zone_?([0-9]{1,2})(?:$|[_\-.])", re.I),
]

_PROG_PATTERNS = [
    re.compile(r"(?:\bprogramma\b|\bprogram\b)\s*([0-9]{1,3})", re.I),
    re.compile(r"(?:^|[_\.-])prog(?:ramma)?_?([0-9]{1,3})(?:$|[_\.-])", re.I),
    re.compile(r"(?:^|[_\.-])([0-9]{1,3})(?=[_.-]?(?:schedule|sched|progress|progresso))", re.I),
]

def _safe_int(v):
    try:
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip()
        if s == "":
            return None
        return int(float(s))
    except Exception:
        return None

def _safe_float(v):
    try:
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        s = str(v).strip().replace(',', '.')
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

def _quick_sequence_snapshot():
    with QUICK_SEQUENCE_LOCK:
        snap = dict(QUICK_SEQUENCE_STATE)
        snap["zones"] = list(QUICK_SEQUENCE_STATE.get("zones") or [])
    now = time.time()
    end_at = snap.get("current_end_at")
    if snap.get("active") and end_at:
        try:
            snap["remaining_seconds"] = max(0, int(float(end_at) - now))
        except Exception:
            snap["remaining_seconds"] = None
    else:
        snap["remaining_seconds"] = None
    return snap

def _extract_id_from_attrs(attrs, keys):
    if not isinstance(attrs, dict):
        return None
    for k in keys:
        if k in attrs:
            zi = _safe_int(attrs.get(k))
            if zi is not None:
                return zi
    return None

def _extract_zone_id(entity_id, attrs):
    # Prefer explicit attributes (typical integrations expose zone_id)
    zi = _extract_id_from_attrs(attrs, ("zone_id", "zone", "irrigation_zone", "irrigazione_zone", "id_zona"))
    if zi is not None:
        return zi

    # Support entity_ids that start with a numeric zone id (e.g. switch.6, number.6_durata)
    try:
        obj = str(entity_id or "").split(".", 1)[1]
        m = re.match(r"^([0-9]{1,2})(?:$|[_\\-.])", obj)
        if m:
            zi = _safe_int(m.group(1))
            if zi is not None:
                return zi
    except Exception:
        pass

    hay = " ".join([str(entity_id or ""), str((attrs or {}).get("friendly_name") or ""), str((attrs or {}).get("name") or "")])
    for rx in _ZONE_PATTERNS:
        mm = rx.search(hay)
        if mm:
            zi = _safe_int(mm.group(1))
            if zi is not None:
                return zi
    return None

def _extract_program_id(entity_id, attrs):
    pi = _extract_id_from_attrs(attrs, ("program_id", "programma_id", "id_programma"))
    if pi is not None:
        return pi
    hay = " ".join([str(entity_id or ""), str((attrs or {}).get("friendly_name") or ""), str((attrs or {}).get("name") or "")])
    hay_l = hay.lower()
    if "zona" in hay_l or "zone" in hay_l or "zona_" in hay_l:
        return None
    # Avoid classifying zone sensors (especially numeric ones like sensor.6_progresso) as programs
    if any(k in hay_l for k in ("durata", "remaining", "resid", "progresso", "progress")):
        return None
    for rx in _PROG_PATTERNS:
        mm = rx.search(hay)
        if mm:
            pi = _safe_int(mm.group(1))
            if pi is not None:
                return pi
    return None

def _kw(hay, *words):
    h = (hay or "").lower()
    return any(w.lower() in h for w in words)

def _pick_best(cands, predicate):
    # return first candidate matching predicate else first element
    for c in cands:
        if predicate(c):
            return c
    return cands[0] if cands else None

def build_zones_from_entities(entities):
    """Build UI zones from an entity list (states-like dicts).

    This is designed to work well with the e_dry integration, but it's
    generic: it tries to group entities by zone_id/regex and then map
    to switch/remaining/duration/progress/ignore_meteo.
    """
    overrides = {}
    try:
        with open('/data/zone_names.json', 'r', encoding='utf-8') as f:
            overrides = json.load(f) or {}
    except Exception:
        overrides = {}

    # Normalize records
    recs = []
    for e in (entities or []):
        if not isinstance(e, dict):
            continue
        eid = e.get("entity_id")
        if not eid or "." not in eid:
            continue
        attrs = e.get("attributes") or {}
        recs.append({
            "entity_id": eid,
            "domain": eid.split(".", 1)[0],
            "state": e.get("state"),
            "attributes": attrs,
            "zone_id": _extract_zone_id(eid, attrs),
        })

    # Group by zone_id
    groups = {}
    unassigned = []
    for r in recs:
        if r["zone_id"] is None:
            unassigned.append(r)
            continue
        groups.setdefault(r["zone_id"], []).append(r)

    zones = []
    for zone_id in sorted(groups.keys()):
        items = groups[zone_id]
        # Switch for zone
        switch_cands = [r for r in items if r["domain"] == "switch" and not _kw(r["entity_id"], "program") and not _kw((r["attributes"] or {}).get("friendly_name",""), "programma")]
        zone_sw = _pick_best(switch_cands, lambda r: _kw(r["entity_id"], "zona", "zone") or _kw((r["attributes"] or {}).get("friendly_name",""), "zona", "zone"))

        name = None
        if zone_sw:
            eid = zone_sw["entity_id"]
            name = overrides.get(f"zone:{zone_id}") or overrides.get(eid) or (zone_sw["attributes"] or {}).get("friendly_name") or eid
        else:
            # fallback any entity friendly name
            any_e = items[0]
            name = overrides.get(f"zone:{zone_id}") or overrides.get(any_e["entity_id"]) or (any_e["attributes"] or {}).get("friendly_name") or f"Zona {zone_id}"

        # Best-effort: aggancia entitÃƒÂ  senza zone_id che nel friendly_name contengono il nome zona
        try:
            zone_name_low = str(name or "").lower()
            zone_slug = re.sub(r"[^a-z0-9]+", "_", zone_name_low)
            zone_slug_nodigit = re.sub(r"[0-9]+", "", zone_slug)
            # estrai base (prima di un "-")
            zone_base = zone_name_low.split("-")[0].strip() if zone_name_low else ""
            extra = []
            for r in list(unassigned):
                fn = str((r.get("attributes") or {}).get("friendly_name") or "").lower()
                eid_low = r.get("entity_id","").lower()
                if zone_name_low and zone_name_low in fn:
                    extra.append(r); unassigned.remove(r); continue
                if zone_base and zone_base in fn:
                    extra.append(r); unassigned.remove(r); continue
                if zone_slug and zone_slug in eid_low:
                    extra.append(r); unassigned.remove(r); continue
                if zone_slug_nodigit and zone_slug_nodigit and zone_slug_nodigit in eid_low:
                    extra.append(r); unassigned.remove(r); continue
            if extra:
                items = items + extra
        except Exception:
            pass

        # Duration (number/input_number)
        dur_cands = [r for r in items if r["domain"] in ("number","input_number") and (_kw(r["entity_id"], "dur", "duration", "tempo") or _kw((r["attributes"] or {}).get("friendly_name",""), "durata", "duration", "tempo"))]
        dur = _pick_best(dur_cands, lambda r: True)
        # Configured duration (sensor)
        dur_cfg_cands = [r for r in items if r["domain"] == "sensor" and (_kw(r["entity_id"], "durata_configurata","durata_config","configurata") or _kw((r["attributes"] or {}).get("friendly_name",""), "durata configurata","durata_configurata","configurata"))]
        dur_cfg = _pick_best(dur_cfg_cands, lambda r: True)
        # Smart/meteo duration
        dur_smart_cands = [r for r in items if r["domain"] == "sensor" and (_kw(r["entity_id"], "durata_smart","durata_meteo","smart_duration","meteo") or _kw((r["attributes"] or {}).get("friendly_name",""), "durata smart","durata meteo","smart","meteo"))]
        dur_smart = _pick_best(dur_smart_cands, lambda r: True)
        # fallback: cerca in tutti i recs con friendly_name che contiene il nome zona + "durata meteo"
        if not dur_smart:
            for r in recs:
                if r.get("domain") != "sensor":
                    continue
                fname = str((r.get("attributes") or {}).get("friendly_name","")).lower()
                if not fname:
                    continue
                if (zone_name_low and zone_name_low.split("-")[0].strip() in fname) and ("durata meteo" in fname or "durata smart" in fname):
                    dur_smart = r
                    break
        # Effective duration
        dur_eff_cands = [r for r in items if r["domain"] == "sensor" and (_kw(r["entity_id"], "durata_eff","durata_effettiva","effective") or _kw((r["attributes"] or {}).get("friendly_name",""), "durata effettiva","effettiva"))]
        dur_eff = _pick_best(dur_eff_cands, lambda r: True)

        # Remaining (sensor)
        rem_cands = [r for r in items if r["domain"] == "sensor" and (_kw(r["entity_id"], "resid", "remaining") or _kw((r["attributes"] or {}).get("friendly_name",""), "resid", "riman", "remaining"))]
        rem = _pick_best(rem_cands, lambda r: True)

        # Progress / percent (sensor)
        def _is_percent(r):
            u = str((r["attributes"] or {}).get("unit_of_measurement") or "")
            return "%" in u or _kw(r["entity_id"], "progress", "progresso", "percent") or _kw((r["attributes"] or {}).get("friendly_name",""), "progress", "progresso", "percent")
        pct_cands = [r for r in items if r["domain"] == "sensor" and _is_percent(r)]
        pct = _pick_best(pct_cands, lambda r: True)

        # Ignore meteo (input_boolean/switch)
        ign_cands = [r for r in items if r["domain"] in ("input_boolean","switch") and (_kw(r["entity_id"], "ignore") and _kw(r["entity_id"], "meteo","weather") or _kw((r["attributes"] or {}).get("friendly_name",""), "ignora", "meteo", "weather"))]
        ign = _pick_best(ign_cands, lambda r: True)
        # fallback: se non trovato, prova nel set completo usando il suffisso zona
        if not ign and zone_id is not None:
            suffixes = (f"_{zone_id}", f"-{zone_id}")
            # prova a cercare nei recs
            for r in recs:
                if r.get("domain") not in ("switch","input_boolean"):
                    continue
                if not (_kw(r.get("entity_id"), "ignore") and _kw(r.get("entity_id"), "meteo","weather") or _kw((r.get("attributes") or {}).get("friendly_name",""), "ignora", "meteo", "weather")):
                    continue
                eid_lower = r.get("entity_id","").lower()
                if any(eid_lower.endswith(suf) for suf in suffixes):
                    ign = r
                    break
            # se ancora nulla, prova direttamente da HA con naming noto
            if not ign:
                candidates = [
                    f"switch.ignora_meteo_{zone_id}",
                    f"input_boolean.ignora_meteo_{zone_id}",
                    f"switch.ignore_meteo_{zone_id}",
                    f"input_boolean.ignore_meteo_{zone_id}",
                ]
                for ceid in candidates:
                    st = ha_try_get_state(ceid)
                    if st:
                        ign = {"entity_id": ceid, "state": st.get("state"), "attributes": st.get("attributes") or {}, "zone_id": zone_id, "domain": ceid.split(".",1)[0]}
                        break
        # Compute UI fields
        is_on = False
        try:
            if zone_sw:
                is_on = str(zone_sw.get("state","")).lower() in ("on","true","open")
            elif pct and pct.get("state") not in (None, "unknown", "unavailable", ""):
                is_on = float(str(pct.get("state")).replace(",", ".")) > 0
            elif rem and rem.get("state"):
                srem = str(rem.get("state")).strip()
                is_on = srem not in ("0", "0.0", "00:00", "00:00:00", "unknown", "unavailable", "")
        except Exception:
            is_on = False

        z = {
            "id": int(zone_id),
            "name": name,
            "switch": zone_sw["entity_id"] if zone_sw else None,
            "state": zone_sw["state"] if zone_sw else None,
            "is_on": is_on,

            "remaining_entity": rem["entity_id"] if rem else None,
            "remaining": rem["state"] if rem else None,
            "remaining_raw": rem["state"] if rem else None,
            "remaining_attrs": rem["attributes"] if rem else {},

            "duration_entity": dur["entity_id"] if dur else None,
            "duration": _safe_int(dur["state"]) if dur else None,
            "duration_raw": dur["state"] if dur else None,
            "duration_attrs": dur["attributes"] if dur else {},
            "duration_configured_entity": dur_cfg["entity_id"] if dur_cfg else None,
            "duration_configured": _safe_int(dur_cfg["state"]) if dur_cfg else None,
            "duration_configured_raw": dur_cfg["state"] if dur_cfg else None,
            "duration_configured_attrs": dur_cfg["attributes"] if dur_cfg else {},
            "duration_smart_entity": dur_smart["entity_id"] if dur_smart else None,
            "duration_smart": _safe_int(dur_smart["state"]) if dur_smart else None,
            "duration_smart_raw": dur_smart["state"] if dur_smart else None,
            "duration_smart_attrs": dur_smart["attributes"] if dur_smart else {},
            "duration_effective_entity": dur_eff["entity_id"] if dur_eff else None,
            "duration_effective": _safe_int(dur_eff["state"]) if dur_eff else None,
            "duration_effective_raw": dur_eff["state"] if dur_eff else None,
            "duration_effective_attrs": dur_eff["attributes"] if dur_eff else {},

            "percent_entity": pct["entity_id"] if pct else None,
            "percent": None,
            "percent_raw": pct["state"] if pct else None,
            "percent_attrs": pct["attributes"] if pct else {},
            "percent_unit": (pct["attributes"] or {}).get("unit_of_measurement") if pct else None,
            "percent_interpretation": "percent",
            "ignore_meteo_entity": ign["entity_id"] if ign else None,
            "ignore_meteo_state": ign["state"] if ign else None,
            "ignore_meteo_attrs": ign.get("attributes") if ign else {},

            "computed": {"remaining": False, "percent": False, "duration": False},
            "missing": {"switch": zone_sw is None, "remaining": rem is None, "duration": dur is None, "percent": pct is None},
        }

        # parse percent numeric if possible
        if pct and pct.get("state") not in (None, "unknown", "unavailable"):
            try:
                z["percent"] = float(str(pct.get("state")).replace(",", "."))
                # if unit not %, treat as energy/other
                u = str((pct.get("attributes") or {}).get("unit_of_measurement") or "")
                if "%" not in u:
                    z["percent_interpretation"] = "energy"
            except Exception:
                z["percent"] = None
        zones.append(z)

    # Fallback if nothing grouped
    if zones:
        return zones

    # No zone_id grouping available -> reuse existing fuzzy switch discovery
    return discover_zones(strict_config_entry=None)

def build_programs_from_entities(entities):
    """Extract program switch + related sensors from entities list."""
    recs = []
    for e in (entities or []):
        if not isinstance(e, dict):
            continue
        eid = e.get("entity_id")
        if not eid or "." not in eid:
            continue
        attrs = e.get("attributes") or {}
        recs.append({
            "entity_id": eid,
            "domain": eid.split(".", 1)[0],
            "state": e.get("state"),
            "attributes": attrs,
            "program_id": _extract_program_id(eid, attrs),
        })

    # programs enabled entity
    enabled = _pick_best(
        [r for r in recs if r["domain"] == "switch" and (_kw(r["entity_id"], "programmi_abilitati","programs_enabled") or _kw((r["attributes"] or {}).get("friendly_name",""), "programmi abilitati", "programs enabled"))],
        lambda r: True
    )

    # arricchisci con definizioni da options (giorni/zone/pause)
    def _as_list(v):
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            return list(v)
        try:
            s = str(v).strip()
            if not s:
                return []
            return [x.strip() for x in s.split(",") if x.strip()]
        except Exception:
            return []

    def _as_float(v):
        try:
            return float(v)
        except Exception:
            return None

    program_defs = {}
    opts_prog = read_options() or {}
    for d in opts_prog.get('programs') or []:
        try:
            pid_def = int(d.get('id') or d.get('program_id') or 0)
        except Exception:
            pid_def = None
        if pid_def is None:
            continue
        program_defs[pid_def] = d

    groups = {}
    for r in recs:
        if r["program_id"] is None:
            continue
        groups.setdefault(r["program_id"], []).append(r)

    programs = []
    for pid in sorted(groups.keys()):
        items = groups[pid]
        sw = _pick_best([r for r in items if r["domain"] == "switch"], lambda r: _kw(r["entity_id"], "program", "programma") or _kw((r["attributes"] or {}).get("friendly_name",""), "program", "programma"))
        sched = _pick_best([r for r in items if r["domain"] == "sensor" and (_kw(r["entity_id"], "sched","schedule","orario") or _kw((r["attributes"] or {}).get("friendly_name",""), "sched", "orario"))], lambda r: True)
        prog = _pick_best([r for r in items if r["domain"] == "sensor" and (_kw(r["entity_id"], "progress","progresso") or "%" in str((r["attributes"] or {}).get("unit_of_measurement") or ""))], lambda r: True)
        stop_btn = _pick_best([r for r in items if r["domain"] in ("button","input_button") and _kw(r["entity_id"], "stop")], lambda r: True)

        name = (sw or sched or prog or items[0]).get("attributes", {}).get("friendly_name") or f"Programma {pid}"
        prog_def = program_defs.get(pid, {}) or {}

        # prefer sensing from schedule sensor attributes (integration)
        sched_attrs = (sched or {}).get("attributes") or {}
        state_val = sw["state"] if sw else prog_def.get("enabled")
        if state_val is None:
            state_val = sched_attrs.get("enabled")

        schedule_val = sched["state"] if sched else None
        if schedule_val in (None, "", "disabled", "unavailable", "unknown"):
            schedule_val = sched_attrs.get("time") or prog_def.get("time")

        days_def = _as_list(sched_attrs.get("days") or sched_attrs.get("weekdays") or prog_def.get("days") or prog_def.get("weekdays"))

        zones_def = sched_attrs.get("zones") or prog_def.get("zones") or []
        if not isinstance(zones_def, list):
            zones_def = _as_list(zones_def)

        pause_def = sched_attrs.get("pause_minutes")
        if pause_def is None:
            pause_def = prog_def.get("pause_minutes")
        if pause_def is None:
            pause_def = prog_def.get("pause_minuti")
        pause_def = _as_float(pause_def)

        progress_val = prog["state"] if prog else None
        if prog and prog.get("state") not in (None, "unknown", "unavailable"):
            try:
                progress_val = float(str(prog.get("state")).replace(",", "."))
            except Exception:
                progress_val = prog.get("state")

        programs.append({
            "program_id": int(pid),
            "name": name,
            "program_switch": sw["entity_id"] if sw else None,
            "program_state": state_val,
            "schedule": schedule_val,
            "time": sched_attrs.get("time") or prog_def.get("time"),
            "enabled": state_val,
            "progress": progress_val,
            "stop_button": stop_btn["entity_id"] if stop_btn else None,
            "days": days_def,
            "zones": zones_def,
            "pause_minutes": pause_def,
            "missing": {
                "program_switch": sw is None,
                "schedule": sched is None,
                "progress": prog is None,
                "stop_button": stop_btn is None,
            }
        })

    enabled_state = enabled["state"] if enabled else None
    enabled_entity = enabled["entity_id"] if enabled else None
    return enabled_state, enabled_entity, programs

def ha_try_get_state(entity_id: str):
    try:
        return ha_get_state(entity_id)
    except Exception:
        return None


@app.route('/api/programs/update', methods=['POST'])
def programs_update():
    """Proxy to integration service e_dry.update_program (create/update/delete)."""
    try:
        payload = request.get_json(silent=True) or {}
        pid = payload.get('program_id')
        if pid is None:
            return jsonify({
            "version": VERSION,'error': 'program_id richiesto'}), 400
        # Normalize fields to avoid name duplication and invalid time values
        if 'name' in payload and payload.get('name') is not None:
            raw = str(payload.get('name') or '')
            cleaned = raw
            cleaned = re.sub(r"Centralina\\s+Irrigazione", "", cleaned, flags=re.I)
            cleaned = re.sub(r"\\s*-?\\s*schedule\\b", "", cleaned, flags=re.I)
            cleaned = re.sub(r"\\s+", " ", cleaned).strip(" -")
            cleaned = re.sub(r"^Programma\\s+", "", cleaned, flags=re.I).strip(" -")
            payload['name'] = f"Programma {cleaned}" if cleaned else "Programma"
        if 'time' in payload:
            t = payload.get('time')
            if t in (None, "", "disabled", "unavailable", "unknown"):
                payload.pop('time', None)
        ha_call_service('e_dry', 'update_program', payload)
        return jsonify({"version": VERSION,'ok': True})
    except Exception as e:
        return jsonify({"version": VERSION,'error': str(e)}), 500

@app.route('/api/programs/create', methods=['POST'])
def programs_create():
    """Create a persistent e_dry irrigation program."""
    try:
        payload = request.get_json(silent=True) or {}
        name = str(payload.get('name') or '').strip()
        time_val = str(payload.get('time') or '').strip()
        days = payload.get('days') or []
        zones = payload.get('zones') or []

        if not name:
            return jsonify({"version": VERSION, 'error': 'name richiesto'}), 400
        if not re.match(r'^\d{1,2}:\d{2}$', time_val):
            return jsonify({"version": VERSION, 'error': 'time richiesto in formato HH:MM'}), 400
        if not isinstance(days, list) or not days:
            return jsonify({"version": VERSION, 'error': 'seleziona almeno un giorno'}), 400
        if not isinstance(zones, list) or not zones:
            return jsonify({"version": VERSION, 'error': 'seleziona almeno una zona'}), 400

        cleaned = re.sub(r"Centralina\s+Irrigazione", "", name, flags=re.I)
        cleaned = re.sub(r"\s*-?\s*schedule\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
        cleaned = re.sub(r"^Programma\s+", "", cleaned, flags=re.I).strip(" -")

        create_payload = {
            'name': f"Programma {cleaned}" if cleaned else "Programma",
            'time': time_val,
            'days': [str(d).strip() for d in days if str(d).strip()],
            'zones': zones,
            'pause_minutes': float(payload.get('pause_minutes') or 0),
            'enabled': bool(payload.get('enabled', True)),
        }
        try:
            ha_call_service('e_dry', 'create_program', create_payload)
        except requests.HTTPError:
            fallback_payload = dict(create_payload)
            fallback_payload['program_id'] = 0
            ha_call_service('e_dry', 'update_program', fallback_payload)
        return jsonify({"version": VERSION, 'ok': True})
    except Exception as e:
        return jsonify({"version": VERSION, 'error': str(e)}), 500


def discover_zones(strict_config_entry=None):
    """Discover zones and return list of zone objects expected by UI."""
    opts = read_options()
    explicit_include = opts.get('zone_entities') or []
    explicit_exclude = set(opts.get('exclude_entities') or [])

    def _is_program_entity(eid, attrs):
        if not eid:
            return False
        e_lower = eid.lower()
        fn = (attrs or {}).get('friendly_name') or ''
        fn_lower = str(fn).strip().lower()
        keywords = ('program', 'programma', 'programmi', 'schedule', 'automation', 'programma_ab', 'centralina')
        return any(k in fn_lower or k in e_lower for k in keywords)

    try:
        if strict_config_entry:
            entities = resolve_entities_by_config_entry(strict_config_entry)
            entities_filtered = []
            states = []
            for e in entities:
                if not isinstance(e, dict):
                    continue
                eid = e.get("entity_id")
                if not eid or '.' not in eid:
                    continue
                if eid in explicit_exclude:
                    continue
                if _is_program_entity(eid, e.get('attributes')):
                    continue
                if explicit_include and (eid not in explicit_include):
                    continue
                entities_filtered.append(e)
                domain = eid.split('.', 1)[0]
                if domain in ('switch', 'binary_sensor', 'light'):
                    states.append(e)
            if entities_filtered:
                return build_zones_from_entities(entities_filtered)
            return build_zones_from_states(states)

        all_states = ha_get_states_all()
        candidates = []
        prog_keywords = ('program', 'programma', 'programmi', 'schedule', 'automation', 'programma_ab', 'centralina')

        for s in all_states:
            eid = s.get('entity_id', '')
            if not eid:
                continue
            domain = eid.split('.', 1)[0]
            attrs = s.get('attributes', {}) or {}
            fname = (attrs.get('friendly_name') or '')
            fname_norm = str(fname).strip().lower()
            name_eid = eid.lower()

            if eid in explicit_exclude:
                continue
            if explicit_include and (eid not in explicit_include):
                continue
            if _is_program_entity(eid, attrs) or any(k in name_eid for k in prog_keywords):
                continue

            if domain in ('switch', 'light', 'binary_sensor') and (
                'zona' in fname_norm or 'zona' in name_eid or
                'valvol' in fname_norm or
                'irrig' in name_eid or
                'sprinkler' in name_eid or
                'giardino' in name_eid
            ):
                candidates.append(s)

        if not candidates:
            for s in all_states:
                eid = s.get('entity_id', '')
                if not eid:
                    continue
                domain = eid.split('.', 1)[0]
                name_eid = eid.lower()
                attrs = s.get('attributes', {}) or {}
                if eid in explicit_exclude:
                    continue
                if explicit_include and (eid not in explicit_include):
                    continue
                if _is_program_entity(eid, attrs) or any(k in name_eid for k in prog_keywords):
                    continue
                if domain == 'switch':
                    candidates.append(s)

        return build_zones_from_states(candidates)
    except Exception:
        # fail-safe
        return []


def build_zones_from_states(states_list):
    zones = []
    seen = set()
    idx = 1
    try:
        with open('/data/zone_names.json', 'r', encoding='utf-8') as f:
            _name_overrides = json.load(f) or {}
    except Exception:
        _name_overrides = {}

    for s in states_list:
        eid = s.get('entity_id')
        if not eid or eid in seen:
            continue
        seen.add(eid)
        attrs = s.get('attributes') or {}
        is_on = str(s.get('state', '')).lower() in ('on', 'true', 'open')
        # try to resolve ignore_meteo companion by zone_id pattern
        zone_id = _extract_zone_id(eid, attrs)
        ignore_entity = None
        ignore_state = None
        ignore_attrs = {}
        if zone_id is not None:
            candidates = [
                f"switch.ignora_meteo_{zone_id}",
                f"input_boolean.ignora_meteo_{zone_id}",
                f"switch.ignore_meteo_{zone_id}",
                f"input_boolean.ignore_meteo_{zone_id}",
            ]
            for ceid in candidates:
                st = ha_try_get_state(ceid)
                if st:
                    ignore_entity = ceid
                    ignore_state = st.get('state')
                    ignore_attrs = st.get('attributes') or {}
                    break
        zones.append({
            'id': idx,
            'name': _name_overrides.get(f"zone:{idx}") or _name_overrides.get(eid) or attrs.get('friendly_name') or eid,
            'switch': eid,
            'state': s.get('state'),
            'is_on': is_on,
            'remaining_entity': None,
            'remaining': None,
            'remaining_raw': None,
            'remaining_attrs': {},
            'duration_entity': None,
            'duration': None,
            'duration_raw': None,
            'duration_attrs': {},
            'duration_configured_entity': None,
            'duration_configured': None,
            'duration_configured_raw': None,
            'duration_configured_attrs': {},
            'duration_smart_entity': None,
            'duration_smart': None,
            'duration_smart_raw': None,
            'duration_smart_attrs': {},
            'duration_effective_entity': None,
            'duration_effective': None,
            'duration_effective_raw': None,
            'duration_effective_attrs': {},
            'percent_entity': None,
            'percent': None,
            'percent_raw': None,
            'percent_attrs': {},
            'percent_unit': None,
            'percent_interpretation': 'percent',
            'ignore_meteo_entity': ignore_entity,
            'ignore_meteo_state': ignore_state,
            'ignore_meteo_attrs': ignore_attrs,
            'computed': {'remaining': False, 'percent': False, 'duration': False},
            'missing': {'switch': False, 'remaining': True, 'duration': True, 'percent': True}
        })
        idx += 1
        if idx > 48:
            break
    return zones


def _write_name_override(entity_id, name, zone_id=None):
    path = '/data/zone_names.json'
    try:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
        except Exception:
            data = {}
        keys = []
        if entity_id:
            keys.append(entity_id)
        if zone_id is not None:
            keys.append(f"zone:{zone_id}")
        for k in keys:
            if not name:
                data.pop(k, None)
            else:
                data[k] = str(name)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


@app.route('/api/irrigazione/zone/rename', methods=['POST'])
def zone_rename():
    data = request.get_json(silent=True) or {}
    entity_id = data.get('entity_id')
    new_name = data.get('name')
    zone_id = data.get('zone_id')
    base_minutes = data.get('base_minutes')
    ignore_weather = data.get('ignore_weather')

    if not entity_id and zone_id is None:
        return jsonify({
        "version": VERSION,'error': 'entity_id o zone_id richiesto'}), 400

    # resolve zone_id from entity_id if missing
    if zone_id is None and entity_id:
        try:
            zones = discover_zones(read_options().get('bind_config_entry_id'))
            match = next((z for z in zones if z.get('switch') == entity_id), None)
            if match:
                zone_id = match.get('id')
        except Exception:
            zone_id = None

    payload = {}
    if zone_id is not None:
        try:
            payload['zone_id'] = int(zone_id)
        except Exception:
            payload['zone_id'] = zone_id
    if entity_id:
        payload['entity_id'] = entity_id
    if new_name is not None:
        payload['name'] = new_name
    if base_minutes is not None:
        payload['base_minutes'] = base_minutes
    if ignore_weather is not None:
        payload['ignore_weather'] = ignore_weather

    try:
        ha_call_service('e_dry', 'update_zone', payload)
        _write_name_override(entity_id, new_name, zone_id=zone_id)
        return jsonify({
        "version": VERSION,'ok': True, 'entity_id': entity_id, 'zone_id': zone_id, 'name': new_name})
    except Exception as e:
        return jsonify({
        "version": VERSION,'error': str(e)}), 500


def _merge_zone_lists(cache_zones, new_zones):
    """Unisci le liste di zone mantenendo la lunghezza massima possibile.

    Se la risposta nuova ha meno zone (o zero), usa la cache per riempire i buchi.
    Match per id; se mancano id, preserva comunque l'ordine della cache.
    """
    cache_zones = cache_zones or []
    new_zones = new_zones or []
    if not cache_zones:
        return new_zones
    if not new_zones:
        return cache_zones

    merged_by_id = {}
    for z in new_zones:
        zid = z.get('id')
        merged_by_id[zid] = z
    for zc in cache_zones:
        zid = zc.get('id')
        if zid not in merged_by_id:
            merged_by_id[zid] = zc
    # ordina per id se presente, altrimenti lascia l'ordine della cache
    try:
        merged = sorted(merged_by_id.values(), key=lambda x: x.get('id') or 0)
    except Exception:
        merged = list(merged_by_id.values())
    return merged


@app.route('/api/irrigazione/state')
def api_irrigazione_state():
    opts = read_options()
    bind = opts.get('bind_config_entry_id') or request.args.get('config_entry')

    # Aggregated sensors (created by the integration)
    zones_info_entity = opts.get('zones_info_entity') or 'sensor.e_dry_zones_info'
    programs_info_entity = opts.get('programs_info_entity') or 'sensor.e_dry_programs_info'
    meteo_info_entity = opts.get('meteo_info_entity') or 'sensor.e_dry_meteo_info'
    programs_enabled_entity = opts.get('programs_enabled_entity') or 'switch.programmi_abilitati'

    entities = None

    def _as_bool(v):
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        try:
            s = str(v).strip().lower()
        except Exception:
            return None
        if s in ('on', 'true', '1', 'yes', 'y'):
            return True
        if s in ('off', 'false', '0', 'no', 'n', ''):
            return False
        return None

    def _fmt_remaining(sec):
        try:
            s = int(float(sec))
            if s < 0:
                s = 0
            m, s2 = divmod(s, 60)
            if m >= 60:
                h, m2 = divmod(m, 60)
                return f"{h:02d}:{m2:02d}:{s2:02d}"
            return f"{m:02d}:{s2:02d}"
        except Exception:
            return '00:00'

    def _norm(s: str) -> str:
        try:
            return str(s or '').strip().lower()
        except Exception:
            return ''

    def _contains_name(hay: str, needle: str) -> bool:
        h = _norm(hay)
        n = _norm(needle)
        if not h or not n:
            return False
        return n in h

    # Strict: resolve zones info from configured entity_id, otherwise from bind entities (no global discovery)
    z_info = ha_try_get_state(zones_info_entity)
    z_list = []
    if z_info:
        z_list = ((z_info.get('attributes') or {}).get('zones') or [])

    # Auto-bind: infer config_entry from zones_info unique_id_prefix if missing
    if not bind and z_list:
        try:
            uip = str((z_list[0] or {}).get('unique_id_prefix') or '')
            if '_zone_' in uip:
                bind = uip.split('_zone_', 1)[0]
        except Exception:
            pass

    if bind and entities is None:
        try:
            entities = resolve_entities_by_config_entry(bind) or []
        except Exception:
            entities = []
        if not entities:
            entities = resolve_entities_by_config_entry_registry(bind) or []

    # Build per-zone entity mapping from bound entities (NO discovery).
    ent_recs = []
    for e in (entities or []):
        if not isinstance(e, dict):
            continue
        eid = e.get('entity_id') or ''
        if '.' not in eid:
            continue
        attrs = e.get('attributes') or {}
        ent_recs.append({
            'entity_id': eid,
            'domain': eid.split('.', 1)[0],
            'state': e.get('state'),
            'attributes': attrs,
            'name': attrs.get('friendly_name') or attrs.get('name') or '',
        })

    by_zone_attr = {}
    try:
        for r in ent_recs:
            zid = _extract_zone_id(r.get('entity_id'), r.get('attributes') or {})
            if zid is None:
                continue
            by_zone_attr.setdefault(int(zid), []).append(r)
    except Exception:
        by_zone_attr = {}

    def _pick(items, predicate):
        for it in items:
            if predicate(it):
                return it
        return None

    def _zone_bucket(zone_id: int, zone_name: str):
        items = list(by_zone_attr.get(zone_id, []))
        zn = _norm(zone_name)
        # Add best-effort matches by name/id patterns, but only from bound entities
        for r in ent_recs:
            if r in items:
                continue
            eid = _norm(r.get('entity_id'))
            nm = _norm(r.get('name'))
            if zn and (zn in nm):
                items.append(r)
                continue
            # common patterns: zona_1_*, sensor.6_remaining, number.7_durata, etc.
            if f'zona_{zone_id}' in eid or eid.startswith(f'sensor.{zone_id}_') or eid.startswith(f'number.{zone_id}_') or eid.startswith(f'switch.{zone_id}') or eid.startswith(f'input_boolean.{zone_id}_'):
                items.append(r)
                continue
        return items

    def _as_float(v):
        try:
            if v is None:
                return None
            return float(str(v).replace(',', '.'))
        except Exception:
            return None

    def _zone_entities(zone_id: int, zone_name: str):
        items = _zone_bucket(zone_id, zone_name)
        zn = zone_name

        def _is_name(it, *parts):
            nm = _norm(it.get('name'))
            return all(_contains_name(nm, p) for p in parts)

        def _eid_has(it, *parts):
            eid = _norm(it.get('entity_id'))
            return all(p in eid for p in parts)

        switch_ent = _pick([i for i in items if i.get('domain') == 'switch'], lambda it: _norm(it.get('name')) == _norm(zn)) \
            or _pick([i for i in items if i.get('domain') == 'switch'], lambda it: _is_name(it, zn))

        duration_ent = _pick([i for i in items if i.get('domain') in ('number', 'input_number')], lambda it: _is_name(it, zn, 'durata') or _eid_has(it, 'durata'))
        remaining_ent = _pick([i for i in items if i.get('domain') == 'sensor'], lambda it: _eid_has(it, 'remaining') or _is_name(it, zn, 'remaining'))
        progress_ent = _pick([i for i in items if i.get('domain') == 'sensor'], lambda it: _eid_has(it, 'progresso') or _is_name(it, zn, 'progresso'))
        ignore_ent = _pick([i for i in items if i.get('domain') in ('switch', 'input_boolean')], lambda it: _is_name(it, zn, 'ignora', 'meteo') or (_eid_has(it, 'ignora') and _eid_has(it, 'meteo')))

        dur_cfg_ent = _pick([i for i in items if i.get('domain') == 'sensor'], lambda it: _eid_has(it, 'durata_configurata') or _is_name(it, zn, 'durata configurata'))
        dur_smart_ent = _pick([i for i in items if i.get('domain') == 'sensor'], lambda it: _eid_has(it, 'durata_smart') or _eid_has(it, 'durata_meteo') or _is_name(it, zn, 'durata meteo') or _is_name(it, zn, 'durata smart'))
        dur_eff_ent = _pick([i for i in items if i.get('domain') == 'sensor'], lambda it: _eid_has(it, 'durata_effettiva') or _is_name(it, zn, 'durata effettiva'))

        return {
            'switch': switch_ent,
            'duration': duration_ent,
            'remaining': remaining_ent,
            'progress': progress_ent,
            'ignore_meteo': ignore_ent,
            'duration_configured': dur_cfg_ent,
            'duration_smart': dur_smart_ent,
            'duration_effective': dur_eff_ent,
        }

    # Build zones from aggregated list + mapping from bound entities (NO fallback to discovery)
    zones = []
    zones_by_id = {}

    def _state_to_rec(st):
        if not st or not isinstance(st, dict):
            return None
        eid = st.get('entity_id') or ''
        if not eid or '.' not in eid:
            return None
        attrs = st.get('attributes') or {}
        return {
            'entity_id': eid,
            'domain': eid.split('.', 1)[0],
            'state': st.get('state'),
            'attributes': attrs,
            'name': attrs.get('friendly_name') or attrs.get('name') or '',
        }

    def _first_existing(candidates):
        for eid in candidates:
            st = ha_try_get_state(eid)
            rec = _state_to_rec(st)
            if rec:
                return rec
        return None
    for zi in (z_list or []):
        zid = _safe_int(zi.get('id'))
        if zid is None:
            continue
        zname = zi.get('name') or f"Zona {zid}"
        mapping = _zone_entities(zid, zname)

        # Deterministic fallbacks when the config_entry mapping is unavailable
        if mapping.get('duration') is None:
            mapping['duration'] = _first_existing([
                f"number.zona_{zid}_durata",
                f"input_number.zona_{zid}_durata",
                f"number.{zid}_durata",
                f"input_number.{zid}_durata",
            ])
        if mapping.get('remaining') is None:
            mapping['remaining'] = _first_existing([
                f"sensor.zona_{zid}_remaining",
                f"sensor.{zid}_remaining",
                f"sensor.centralina_irrigazione_zona_{zid}_remaining",
            ])
        if mapping.get('progress') is None:
            mapping['progress'] = _first_existing([
                f"sensor.zona_{zid}_progresso",
                f"sensor.{zid}_progresso",
                f"sensor.centralina_irrigazione_zona_{zid}_progresso",
            ])
        if mapping.get('ignore_meteo') is None:
            mapping['ignore_meteo'] = _first_existing([
                "switch.ignora_meteo" if zid == 1 else f"switch.ignora_meteo_{zid}",
                f"input_boolean.ignora_meteo_{zid}",
            ])

        z = {
            'id': zid,
            'name': zname,
            'is_on': False,
            'state': None,
            'switch': zi.get('switch_entity_id') or (mapping.get('switch') or {}).get('entity_id'),

            'duration_entity': (mapping.get('duration') or {}).get('entity_id'),
            'duration': _as_float((mapping.get('duration') or {}).get('state')),
            'duration_raw': (mapping.get('duration') or {}).get('state'),
            'duration_attrs': (mapping.get('duration') or {}).get('attributes') or {},

            'duration_configured_entity': (mapping.get('duration_configured') or {}).get('entity_id'),
            'duration_configured_raw': (mapping.get('duration_configured') or {}).get('state'),
            'duration_configured_attrs': (mapping.get('duration_configured') or {}).get('attributes') or {},

            'duration_smart_entity': (mapping.get('duration_smart') or {}).get('entity_id'),
            'duration_smart_raw': (mapping.get('duration_smart') or {}).get('state'),
            'duration_smart_attrs': (mapping.get('duration_smart') or {}).get('attributes') or {},

            'duration_effective_entity': (mapping.get('duration_effective') or {}).get('entity_id'),
            'duration_effective_raw': (mapping.get('duration_effective') or {}).get('state'),
            'duration_effective_attrs': (mapping.get('duration_effective') or {}).get('attributes') or {},

            'remaining_entity': (mapping.get('remaining') or {}).get('entity_id'),
            'remaining_raw': (mapping.get('remaining') or {}).get('state'),
            'remaining': (mapping.get('remaining') or {}).get('state'),
            'remaining_attrs': (mapping.get('remaining') or {}).get('attributes') or {},

            'percent_entity': (mapping.get('progress') or {}).get('entity_id'),
            'percent_raw': (mapping.get('progress') or {}).get('state'),
            'percent': _as_float((mapping.get('progress') or {}).get('state')),
            'percent_attrs': (mapping.get('progress') or {}).get('attributes') or {},
            'percent_unit': ((mapping.get('progress') or {}).get('attributes') or {}).get('unit_of_measurement') or '%',
            'percent_interpretation': 'percent',

            'ignore_meteo_entity': (mapping.get('ignore_meteo') or {}).get('entity_id'),
            'ignore_meteo_state': (mapping.get('ignore_meteo') or {}).get('state'),
            'ignore_meteo_attrs': (mapping.get('ignore_meteo') or {}).get('attributes') or {},

            'computed': {'remaining': False, 'percent': False, 'duration': False},
            'missing': {
                'switch': (mapping.get('switch') is None),
                'remaining': (mapping.get('remaining') is None),
                'duration': (mapping.get('duration') is None),
                'percent': (mapping.get('progress') is None),
            },
        }

        # Overlay authoritative values from zones_info (no calculations)
        active_val = _as_bool(zi.get('active'))
        if active_val is not None:
            z['is_on'] = active_val
            z['state'] = 'on' if active_val else 'off'

        # Use numeric values from aggregated sensor directly for summary fields
        z['duration_configured'] = zi.get('configured_duration')
        z['duration_smart'] = zi.get('smart_duration')
        z['duration_effective'] = zi.get('effective_duration')
        z['profile_id'] = zi.get('profile_id') or 'standard'
        z['profile_name'] = zi.get('profile_name') or 'Standard'
        z['profile_smart_multiplier'] = zi.get('profile_smart_multiplier')
        z['profile_wind_sensitive'] = zi.get('profile_wind_sensitive')

        ign_val = _as_bool(zi.get('ignore_weather'))
        if ign_val is not None:
            z['ignore_meteo_state'] = 'on' if ign_val else 'off'

        # percent already parsed from sensor state (no calculations)

        zones.append(z)
        zones_by_id[zid] = z

    zones = sorted(zones, key=lambda x: x.get('id') or 0)

    # Programs enabled is a real HA switch (bidirectional)
    programs_enabled = None
    try:
        sw = ha_try_get_state(programs_enabled_entity)
        if sw:
            programs_enabled = 'on' if str(sw.get('state')).lower() in ('on', 'true', '1') else 'off'
    except Exception:
        programs_enabled = None

    # Programs list from aggregated programs sensor; enrich with entities for start/stop if bind is available
    programs = []
    legacy_prog_map = {}
    if entities:
        try:
            _es, _ee, legacy_programs = build_programs_from_entities(entities)
            for lp in (legacy_programs or []):
                pid = _safe_int(lp.get('program_id'))
                if pid is not None:
                    legacy_prog_map[pid] = lp
        except Exception:
            legacy_prog_map = {}

    p_info = ha_try_get_state(programs_info_entity)
    if p_info:
        p_list = ((p_info.get('attributes') or {}).get('programs') or [])
        for p in p_list:
            pid = _safe_int(p.get('id'))
            if pid is None:
                continue
            prog_prog = p.get('progress_percent')
            try:
                prog_prog = float(str(prog_prog).replace(',', '.')) if prog_prog is not None else None
            except Exception:
                prog_prog = None
            lp = legacy_prog_map.get(pid) or {}
            programs.append({
                'program_id': pid,
                'name': p.get('name'),
                'program_switch': lp.get('program_switch'),
                'program_state': 'on' if bool(p.get('enabled')) else 'off',
                'schedule': p.get('time'),
                'time': p.get('time'),
                'enabled': bool(p.get('enabled')),
                'progress': prog_prog,
                'running': bool(p.get('running')),
                'current_zone_id': p.get('current_zone_id'),
                'next_zone_id': p.get('next_zone_id'),
                'zone_remaining_seconds': p.get('zone_remaining_seconds'),
                'zone_started_at': p.get('zone_started_at'),
                'zone_end_at': p.get('zone_end_at'),
                'stop_button': lp.get('stop_button'),
                'days': p.get('days') or [],
                'zones': p.get('zones') or [],
                'pause_minutes': p.get('pause_minutes'),
                'zone_durations': p.get('zone_durations') or {},
                'missing': {
                    'program_switch': not bool(lp.get('program_switch')),
                    'schedule': False,
                    'progress': prog_prog is None,
                    'stop_button': not bool(lp.get('stop_button')),
                }
            })

    # Weather from aggregated meteo sensor (fallback to legacy sensors)
    weather = []
    meteo = ha_try_get_state(meteo_info_entity)
    if meteo:
        a = meteo.get('attributes') or {}
        status = a.get('status') or meteo.get('state')
        reason = a.get('reason')
        is_blocking = a.get('is_blocking')
        weather = [
            {
                'entity_id': meteo_info_entity,
                'state': str(a.get('smart_factor') if a.get('smart_factor') is not None else ''),
                'missing': False,
                'attributes': {'friendly_name': 'Fattore Smart Calc', 'icon': 'mdi:calculator', 'state_class': 'measurement'},
            },
            {
                'entity_id': meteo_info_entity,
                'state': str(a.get('smart_reason') if a.get('smart_reason') is not None else ''),
                'missing': False,
                'attributes': {'friendly_name': 'Ragionamento Smart Calc', 'icon': 'mdi:text-box-search-outline'},
            },
            {
                'entity_id': meteo_info_entity,
                'state': str(status if status is not None else ''),
                'missing': False,
                'attributes': {
                    'friendly_name': 'Stato Meteo Irrigazione',
                    'icon': a.get('icon') or 'mdi:weather-partly-cloudy',
                    'is_blocking': is_blocking,
                    'reason': reason,
                },
            },
        ]
    else:
        weather_ids = opts.get('weather_entities') or [
            'sensor.fattore_smart_calc',
            'sensor.ragionamento_smart_calc',
            'sensor.stato_meteo_irrigazione',
        ]
        for wid in weather_ids[:3]:
            st = ha_try_get_state(wid) if wid else None
            if st:
                weather.append({'entity_id': wid, 'state': st.get('state'), 'attributes': st.get('attributes') or {}, 'missing': False})
            else:
                weather.append({'entity_id': wid, 'missing': True})

    # Cache / flicker protection
    use_cache = False
    try:
        cache_zones = LAST_STATE.get('zones') or []
        cache_active = LAST_STATE.get('active_zone')
    except Exception:
        cache_zones = []
        cache_active = None

    if cache_zones:
        merged = _merge_zone_lists(cache_zones, zones)
        if len(merged) > len(zones or []):
            zones = merged
            use_cache = True
    if (not zones or len(zones) == 0) and cache_zones:
        zones = cache_zones
        use_cache = True

    # Active zone (best-effort)
    active_zone = None
    try:
        for z in zones:
            if z.get('is_on'):
                active_zone = z.get('id')
                break
    except Exception:
        active_zone = None
    # Do not reuse cached active_zone when we have authoritative zones_info list
    if active_zone is None and not z_list:
        active_zone = cache_active

    try:
        global LAST_STATE_LOG_TS
        now_log = time.time()
        if now_log - LAST_STATE_LOG_TS >= 30:
            LAST_STATE_LOG_TS = now_log
            print(f"[state] zones={len(zones) if zones else 0} cache={len(cache_zones) if cache_zones else 0} use_cache={use_cache}", flush=True)
    except Exception:
        pass

    if not use_cache and zones:
        try:
            LAST_STATE['zones'] = zones
            LAST_STATE['active_zone'] = active_zone
            global LAST_STATE_TS, LAST_STATE_DIRTY
            LAST_STATE_TS = time.time()
            LAST_STATE_DIRTY = False
        except Exception:
            pass

    # Manual adjustment percent (Regolazione Stagionale) - bidirectional via HA number entity
    manual_adjustment_entity = opts.get('manual_adjustment_entity') or 'number.regolazione_stagionale'
    manual_adjustment = None
    manual_adjustment_attrs = {}
    try:
        st = ha_try_get_state(manual_adjustment_entity)
        if st:
            manual_adjustment = _as_float(st.get('state'))
            manual_adjustment_attrs = st.get('attributes') or {}
        elif meteo:
            ma = (meteo.get('attributes') or {}).get('manual_adjustment_percent')
            if ma is not None:
                manual_adjustment = _as_float(ma)
                manual_adjustment_attrs = {'unit_of_measurement': '%', 'min': 0, 'max': 200, 'step': 10, 'friendly_name': 'Regolazione Stagionale'}
    except Exception:
        pass

    return jsonify({
        'version': VERSION,
        'zones': zones,
        'weather': weather,
        'active_zone': active_zone,
        'programs_enabled_entity': programs_enabled_entity,
        'programs_enabled': programs_enabled,
        'programs': programs,
        'manual_adjustment_entity': manual_adjustment_entity,
        'manual_adjustment': manual_adjustment,
        'manual_adjustment_attrs': manual_adjustment_attrs,
        'quick_sequence': _quick_sequence_snapshot(),
    })


@app.route('/api/meteo/manual_adjustment_set', methods=['POST'])
def meteo_manual_adjustment_set():
    """Set seasonal/manual adjustment percent (number.regolazione_stagionale)."""
    data = request.get_json(silent=True) or {}
    entity_id = data.get('entity_id') or (read_options().get('manual_adjustment_entity') or 'number.regolazione_stagionale')
    value = data.get('value')
    if value is None:
        return jsonify({"version": VERSION, 'error': 'value richiesto'}), 400
    try:
        domain = entity_id.split('.', 1)[0] if entity_id and '.' in entity_id else 'number'
        if domain not in ('number', 'input_number'):
            return jsonify({"version": VERSION, 'error': 'entity_id non supportata', 'entity_id': entity_id}), 400
        ha_call_service(domain, 'set_value', {'entity_id': entity_id, 'value': float(value)})
        st = ha_try_get_state(entity_id)
        return jsonify({"version": VERSION, 'ok': True, 'entity_id': entity_id, 'state': st})
    except Exception as e:
        return jsonify({"version": VERSION, 'error': str(e), 'entity_id': entity_id}), 500


def _weather_settings_from_meteo_sensor():
    opts = read_options()
    entity_id = opts.get('meteo_info_entity') or 'sensor.e_dry_meteo_info'
    st = ha_try_get_state(entity_id)
    attrs = (st or {}).get('attributes') or {}
    def val(key, default=None):
        value = attrs.get(key)
        return default if value is None else value
    return {
        'entity_id': entity_id,
        'weather_mode': val('weather_mode'),
        'weather_api_error': val('weather_api_error'),
        'source': val('source'),
        'available': val('available'),
        'age_seconds': val('age_seconds'),
        'enable_smart_calc': val('smart_calc_enabled', True),
        'esunmind_weather_api_url': val('esunmind_weather_api_url', 'http://192.168.3.24:1980/api/weather/irrigation'),
        'weather_max_age_seconds': val('weather_max_age_seconds', 900),
        'forecast_rain_skip_mm': val('forecast_rain_skip_mm', 6),
        'recent_rain_skip_mm': val('recent_rain_skip_mm', 4),
        'rain_sensor_entity_id': val('rain_sensor', 'sensor.e_sunmind_weather_precip_1h_mm'),
        'rain_threshold': val('rain_threshold', 0),
        'temp_sensor_entity_id': val('temp_sensor', 'sensor.e_sunmind_weather_temp_c'),
        'min_temp': val('min_temp', 5),
        'humidity_sensor_entity_id': val('hum_sensor', 'sensor.e_sunmind_weather_humidity_pct'),
        'wind_sensor_entity_id': val('wind_sensor', 'sensor.e_sunmind_weather_wind_ms'),
        'wind_threshold': val('wind_threshold', 20),
    }


def _zone_profiles_from_zones_sensor():
    opts = read_options()
    entity_id = opts.get('zones_info_entity') or 'sensor.e_dry_zones_info'
    st = ha_try_get_state(entity_id)
    attrs = (st or {}).get('attributes') or {}
    profiles = attrs.get('zone_profiles') or []
    zones = attrs.get('zones') or []
    custom_profiles = []
    builtin_ids = {'standard', 'erba', 'fiori', 'piante', 'orto', 'vasi', 'alberi'}
    for profile in profiles:
        if isinstance(profile, dict) and str(profile.get('id') or '') not in builtin_ids:
            custom_profiles.append(profile)
    return {
        'entity_id': entity_id,
        'profiles': profiles if isinstance(profiles, list) else [],
        'custom_profiles': custom_profiles,
        'zones': zones if isinstance(zones, list) else [],
    }


@app.route('/api/meteo/weather_settings', methods=['GET', 'POST'])
def meteo_weather_settings():
    ok, err = _require_token()
    if not ok:
        return err
    data = request.get_json(silent=True) or {}
    ok, err = _require_admin_settings(data)
    if not ok:
        return err
    if request.method == 'GET':
        return jsonify({"version": VERSION, "ok": True, "settings": _weather_settings_from_meteo_sensor()})

    allowed = {
        'enable_smart_calc',
        'esunmind_weather_api_url',
        'weather_max_age_seconds',
        'forecast_rain_skip_mm',
        'recent_rain_skip_mm',
        'rain_threshold',
        'min_temp',
        'wind_threshold',
    }
    payload = {k: data.get(k) for k in allowed if k in data}
    if not payload:
        return jsonify({"version": VERSION, "error": "nessuna taratura da salvare"}), 400
    try:
        ha_call_service('e_dry', 'update_weather_settings', payload)
        return jsonify({"version": VERSION, "ok": True, "settings": _weather_settings_from_meteo_sensor()})
    except Exception as e:
        return jsonify({"version": VERSION, "error": str(e)}), 500


@app.route('/api/irrigazione/zone_profiles', methods=['GET', 'POST'])
def irrigazione_zone_profiles():
    ok, err = _require_token()
    if not ok:
        return err
    data = request.get_json(silent=True) or {}
    ok, err = _require_admin_settings(data)
    if not ok:
        return err
    if request.method == 'GET':
        return jsonify({"version": VERSION, "ok": True, **_zone_profiles_from_zones_sensor()})

    try:
        if 'profiles' in data:
            profiles = data.get('profiles')
            if not isinstance(profiles, list):
                return jsonify({"version": VERSION, "error": "profiles deve essere una lista"}), 400
            ha_call_service('e_dry', 'update_zone_profiles', {'profiles': profiles})

        if 'zone_id' in data and 'profile_id' in data:
            zone_id = _safe_int(data.get('zone_id'))
            profile_id = str(data.get('profile_id') or '').strip()
            if zone_id is None or not profile_id:
                return jsonify({"version": VERSION, "error": "zone_id e profile_id richiesti"}), 400
            ha_call_service('e_dry', 'update_zone', {'zone_id': int(zone_id), 'profile_id': profile_id})

        return jsonify({"version": VERSION, "ok": True, **_zone_profiles_from_zones_sensor()})
    except Exception as e:
        return jsonify({"version": VERSION, "error": str(e)}), 500
@app.route('/api/irrigazione/zone/start', methods=['POST'])
def zone_start():
    data = request.get_json(silent=True) or {}
    zone_raw = data.get('zone_id')
    zone_id = _safe_int(zone_raw)
    if zone_id is None:
        return jsonify({"version": VERSION, 'error': 'zone_id richiesto'}), 400
    duration = _safe_float(data.get('duration') or data.get('minutes'))
    try:
        if duration is not None and duration > 0:
            duration = max(0.1, min(30.0, float(duration)))
            ha_call_service('e_dry', 'start_zone_for', {'zone_id': int(zone_id), 'minutes': float(duration)})
            return jsonify({"version": VERSION, 'ok': True, 'zone_id': int(zone_id), 'minutes': float(duration), 'via': 'e_dry.start_zone_for'})
        ha_call_service('e_dry', 'start_zone', {'zone_id': int(zone_id)})
        return jsonify({"version": VERSION, 'ok': True, 'zone_id': int(zone_id), 'via': 'e_dry.start_zone'})
    except Exception as e:
        return jsonify({"version": VERSION, 'error': str(e), 'zone_id': zone_id}), 500


def _run_quick_sequence(sequence_id, zones, minutes, cancel_event, skip_event):
    current_zid = None
    try:
        for index, zone in enumerate(zones):
            if cancel_event.is_set():
                break
            zid = _safe_int(zone.get('zone_id'))
            if zid is None:
                continue
            try:
                current_zid = int(zid)
                now = time.time()
                with QUICK_SEQUENCE_LOCK:
                    if QUICK_SEQUENCE_STATE.get("sequence_id") == sequence_id:
                        QUICK_SEQUENCE_STATE.update({
                            "active": True,
                            "sequence_id": sequence_id,
                            "zones": list(zones),
                            "minutes": float(minutes),
                            "index": index,
                            "current_zone_id": current_zid,
                            "current_started_at": now,
                            "current_end_at": now + (float(minutes) * 60.0),
                            "next_zone_id": _safe_int(zones[index + 1].get('zone_id')) if index + 1 < len(zones) else None,
                            "status": "running",
                        })
                ha_call_service('e_dry', 'start_zone_for', {'zone_id': int(zid), 'minutes': float(minutes)})
            except Exception:
                traceback.print_exc()
                continue

            deadline = time.time() + (float(minutes) * 60.0)
            cancelled = False
            while time.time() < deadline:
                if cancel_event.is_set():
                    cancelled = True
                    break
                if skip_event.is_set():
                    skip_event.clear()
                    break
                time.sleep(min(1.0, max(0.1, deadline - time.time())))
            try:
                ha_call_service('e_dry', 'stop_zone', {'zone_id': int(zid)})
                current_zid = None
            except Exception:
                traceback.print_exc()
            if cancelled:
                break
    finally:
        if current_zid is not None:
            try:
                ha_call_service('e_dry', 'stop_zone', {'zone_id': int(current_zid)})
            except Exception:
                pass
        with QUICK_SEQUENCE_LOCK:
            if QUICK_SEQUENCE_STATE.get("sequence_id") == sequence_id:
                QUICK_SEQUENCE_STATE.update({
                    "active": False,
                    "index": None,
                    "current_zone_id": None,
                    "current_started_at": None,
                    "current_end_at": None,
                    "next_zone_id": None,
                    "status": "idle" if not cancel_event.is_set() else "stopped",
                })


@app.route('/api/irrigazione/sequence/start', methods=['POST'])
def quick_sequence_start():
    data = request.get_json(silent=True) or {}
    zones = data.get('zones') or []
    minutes = _safe_float(data.get('duration') or data.get('minutes'))
    if not isinstance(zones, list) or not zones:
        return jsonify({"version": VERSION, "error": "seleziona almeno una zona"}), 400
    if minutes is None or minutes <= 0:
        return jsonify({"version": VERSION, "error": "durata non valida"}), 400
    minutes = max(0.1, min(30.0, float(minutes)))
    clean_zones = []
    for item in zones:
        zid = _safe_int((item or {}).get('zone_id') if isinstance(item, dict) else item)
        if zid is not None:
            clean_zones.append({'zone_id': int(zid)})
    if not clean_zones:
        return jsonify({"version": VERSION, "error": "nessuna zona valida"}), 400

    global QUICK_SEQUENCE_THREAD, QUICK_SEQUENCE_ID, QUICK_SEQUENCE_CANCEL, QUICK_SEQUENCE_SKIP
    with QUICK_SEQUENCE_LOCK:
        QUICK_SEQUENCE_CANCEL.set()
        QUICK_SEQUENCE_SKIP.set()
        QUICK_SEQUENCE_CANCEL = threading.Event()
        QUICK_SEQUENCE_SKIP = threading.Event()
        QUICK_SEQUENCE_ID += 1
        seq_id = QUICK_SEQUENCE_ID
        QUICK_SEQUENCE_STATE.update({
            "active": True,
            "sequence_id": seq_id,
            "zones": list(clean_zones),
            "minutes": minutes,
            "index": 0,
            "current_zone_id": None,
            "current_started_at": None,
            "current_end_at": None,
            "next_zone_id": clean_zones[0].get("zone_id") if clean_zones else None,
            "status": "queued",
        })
        QUICK_SEQUENCE_THREAD = threading.Thread(
            target=_run_quick_sequence,
            args=(seq_id, clean_zones, minutes, QUICK_SEQUENCE_CANCEL, QUICK_SEQUENCE_SKIP),
            daemon=True,
        )
        QUICK_SEQUENCE_THREAD.start()

    return jsonify({"version": VERSION, "ok": True, "sequence_id": seq_id, "zones": clean_zones, "minutes": minutes})


@app.route('/api/irrigazione/sequence/skip', methods=['POST'])
def quick_sequence_skip():
    with QUICK_SEQUENCE_LOCK:
        active = bool(QUICK_SEQUENCE_STATE.get("active"))
    if not active:
        return jsonify({"version": VERSION, "ok": False, "error": "nessuna sequenza attiva"}), 400
    QUICK_SEQUENCE_SKIP.set()
    return jsonify({"version": VERSION, "ok": True})


@app.route('/api/irrigazione/zone/stop', methods=['POST'])
def zone_stop():
    data = request.get_json(silent=True) or {}
    zone_raw = data.get('zone_id')
    zone_id = _safe_int(zone_raw)
    if zone_id is None:
        return jsonify({"version": VERSION, 'error': 'zone_id richiesto'}), 400
    try:
        ha_call_service('e_dry', 'stop_zone', {'zone_id': int(zone_id)})
        return jsonify({"version": VERSION, 'ok': True, 'zone_id': int(zone_id), 'via': 'e_dry.stop_zone'})
    except Exception as e:
        return jsonify({"version": VERSION, 'error': str(e), 'zone_id': zone_id}), 500


# compat: alcuni index chiamano /api/irrigazione/zone/stop_all, altri /api/irrigazione/stop_all
@app.route('/api/irrigazione/zone/stop_all', methods=['POST'])
@app.route('/api/irrigazione/stop_all', methods=['POST'])
def stop_all():
    QUICK_SEQUENCE_CANCEL.set()
    QUICK_SEQUENCE_SKIP.set()
    opts = read_options()
    zones_info_entity = opts.get('zones_info_entity') or 'sensor.e_dry_zones_info'
    errors = []

    # Prefer stopping via integration services using the aggregated zones info
    z_info = ha_try_get_state(zones_info_entity)
    if z_info:
        z_list = ((z_info.get('attributes') or {}).get('zones') or [])
        for zi in z_list:
            zid = _safe_int(zi.get('id'))
            if zid is None:
                continue
            if not bool(zi.get('active')):
                continue
            try:
                ha_call_service('e_dry', 'stop_zone', {'zone_id': zid})
            except Exception as e:
                errors.append({'zone_id': zid, 'error': str(e)})

    # Fallback: force-off discovered switches (legacy)
    if not z_info:
        zones = discover_zones(opts.get('bind_config_entry_id'))
        for z in zones:
            eid = z.get('switch')
            if not eid:
                continue
            try:
                ha_call_service('switch', 'turn_off', {'entity_id': eid})
            except Exception as e:
                errors.append({'entity': eid, 'error': str(e)})

    if errors:
        return jsonify({"version": VERSION, 'ok': False, 'errors': errors}), 500
    return jsonify({"version": VERSION, 'ok': True})




# -------------------- PROGRAMS control (best-effort, works with e_dry entities) --------------------
def _get_entities_for_bind():
    opts = read_options()
    bind = opts.get('bind_config_entry_id') or request.args.get('config_entry')
    if not bind:
        return None
    try:
        return resolve_entities_by_config_entry(bind)
    except Exception:
        return None

@app.route('/api/programs/enabled', methods=['POST'])
def programs_enabled_set():
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled'))
    enabled_entity = read_options().get('programs_enabled_entity') or 'switch.programmi_abilitati'
    try:
        domain = enabled_entity.split('.', 1)[0]
        svc = 'turn_on' if enabled else 'turn_off'
        ha_call_service(domain, svc, {'entity_id': enabled_entity})
        return jsonify({'version': VERSION, 'ok': True, 'entity_id': enabled_entity, 'enabled': enabled})
    except Exception as e:
        return jsonify({'version': VERSION, 'error': str(e), 'entity_id': enabled_entity}), 500
@app.route('/api/programs/start', methods=['POST'])
def programs_start():
    data = request.get_json(silent=True) or {}
    pid = data.get('program_id')
    pid = _safe_int(pid)
    if pid is None:
        return jsonify({
        "version": VERSION,'error': 'program_id richiesto'}), 400
    entities = _get_entities_for_bind()
    if not entities:
        return jsonify({
        "version": VERSION,'error': 'bind_config_entry_id mancante o nessuna entitÃƒÂ  risolta'}), 400
    _, _, programs = build_programs_from_entities(entities)
    p = next((x for x in programs if x.get('program_id') == pid), None)
    if not p or not p.get('program_switch'):
        return jsonify({
        "version": VERSION,'error': 'program_switch non trovato', 'program_id': pid}), 404
    try:
        ha_call_service('switch', 'turn_on', {'entity_id': p['program_switch']})
        return jsonify({
        "version": VERSION,'ok': True, 'program_id': pid, 'entity_id': p['program_switch']})
    except Exception as e:
        return jsonify({
        "version": VERSION,'error': str(e), 'program_id': pid, 'entity_id': p.get('program_switch')}), 500

@app.route('/api/programs/stop', methods=['POST'])
def programs_stop():
    data = request.get_json(silent=True) or {}
    pid = _safe_int(data.get('program_id'))
    if pid is None:
        return jsonify({
        "version": VERSION,'error': 'program_id richiesto'}), 400
    try:
        ha_call_service('e_dry', 'stop_programs', {})
        return jsonify({"version": VERSION, "ok": True, "program_id": pid, "via": "e_dry.stop_programs"})
    except Exception:
        pass
    entities = _get_entities_for_bind()
    if not entities:
        return jsonify({
        "version": VERSION,'error': 'bind_config_entry_id mancante o nessuna entitÃƒÂ  risolta'}), 400
    _, _, programs = build_programs_from_entities(entities)
    p = next((x for x in programs if x.get('program_id') == pid), None)
    if not p:
        return jsonify({
        "version": VERSION,'error': 'programma non trovato', 'program_id': pid}), 404
    try:
        # Prefer a stop button if present
        if p.get('stop_button'):
            dom = p['stop_button'].split('.',1)[0]
            # HA button uses button.press; input_button uses input_button.press
            service = 'press'
            ha_call_service(dom, service, {'entity_id': p['stop_button']})
            return jsonify({
        "version": VERSION,'ok': True, 'program_id': pid, 'entity_id': p['stop_button'], 'via': 'button'})
        if p.get('program_switch'):
            ha_call_service('switch', 'turn_off', {'entity_id': p['program_switch']})
            return jsonify({
        "version": VERSION,'ok': True, 'program_id': pid, 'entity_id': p['program_switch'], 'via': 'switch_off'})
        return jsonify({
        "version": VERSION,'error': 'nessuna entitÃƒÂ  stop disponibile', 'program_id': pid}), 404
    except Exception as e:
        return jsonify({
        "version": VERSION,'error': str(e), 'program_id': pid}), 500


@app.route('/api/programs/skip_zone', methods=['POST'])
def programs_skip_zone():
    try:
        ha_call_service('e_dry', 'skip_program_zone', {})
        return jsonify({"version": VERSION, "ok": True, "via": "e_dry.skip_program_zone"})
    except Exception as e:
        return jsonify({"version": VERSION, "error": str(e)}), 500


@app.route('/api/irrigazione/ignore_meteo', methods=['POST'])
def ignore_meteo_set():
    """Toggle ignore_meteo entity (input_boolean/switch) to keep UI in sync with HA."""
    data = request.get_json(silent=True) or {}
    entity_id = data.get('entity_id')
    zone_id = _safe_int(data.get('zone_id'))
    enabled = data.get('enabled')
    if enabled is None:
        return jsonify({"version": VERSION, 'error': 'enabled richiesto'}), 400
    try:
        # Prefer integration service: does not depend on fragile entity_id names
        if zone_id is not None:
            ha_call_service('e_dry', 'update_zone', {'zone_id': int(zone_id), 'ignore_weather': bool(enabled)})
            return jsonify({"version": VERSION, 'ok': True, 'zone_id': int(zone_id), 'state': 'on' if enabled else 'off'})

        if not entity_id:
            return jsonify({"version": VERSION, 'error': 'zone_id o entity_id richiesto'}), 400
        domain = entity_id.split('.', 1)[0]
        if domain not in ('switch', 'input_boolean'):
            return jsonify({
        "version": VERSION,'error': 'entity non supportata', 'entity_id': entity_id}), 400
        svc = 'turn_on' if bool(enabled) else 'turn_off'
        ha_call_service(domain, svc, {'entity_id': entity_id})
        return jsonify({
        "version": VERSION,'ok': True, 'entity_id': entity_id, 'state': 'on' if enabled else 'off'})
    except Exception as e:
        return jsonify({
        "version": VERSION,'error': str(e), 'entity_id': entity_id}), 500


@app.route('/api/irrigazione/duration_set', methods=['POST'])
def duration_set():
    data = request.get_json(silent=True) or {}
    entity_id = data.get('entity_id')
    zone_id = _safe_int(data.get('zone_id'))
    value = data.get('value')
    if value is None:
        return jsonify({"version": VERSION, 'error': 'value richiesto'}), 400
    try:
        ok_any = False
        errors = []
        v = float(value)

        # 1) If we have a numeric entity, set it directly (fast state update)
        if entity_id:
            try:
                domain = entity_id.split('.', 1)[0]
                if domain in ('number', 'input_number'):
                    ha_call_service(domain, 'set_value', {'entity_id': entity_id, 'value': v})
                    ok_any = True
            except Exception as e:
                errors.append(f"{entity_id}: {e}")

        # 2) Persist on the integration (source of truth) if zone_id is provided
        if zone_id is not None:
            try:
                ha_call_service('e_dry', 'update_zone', {'zone_id': int(zone_id), 'base_minutes': v})
                ok_any = True
            except Exception as e:
                errors.append(f"e_dry.update_zone(zone_id={zone_id}): {e}")

        if not ok_any:
            return jsonify({"version": VERSION, 'error': "; ".join(errors) or 'nessuna azione eseguita'}), 500

        # return the updated state for debugging (best-effort)
        st = None
        try:
            if entity_id:
                st = ha_try_get_state(entity_id)
        except Exception:
            st = None

        return jsonify({"version": VERSION, 'ok': True, 'zone_id': zone_id, 'entity_id': entity_id, 'state': st})
    except Exception as e:
        return jsonify({
        "version": VERSION,'error': str(e)}), 500


@app.route('/api/irrigazione/discovery_debug')
def discovery_debug():
    opts = read_options()
    zones = discover_zones(opts.get('bind_config_entry_id'))
    return jsonify({
        "version": VERSION,'bind_config_entry_id': opts.get('bind_config_entry_id'), 'discovered': zones})


@app.route('/addons/irrigazione_dashboard_v2/stats')
@app.route('/addons/local_irrigazione_dashboard/stats')
def addon_stats_shim():
    return jsonify({
        "version": VERSION,
        'result': 'ok',
        'addon': 'irrigazione_dashboard_v2',
        'running': True,
        'uptime_sec': int(time.time() - START_TS)
    })


def ws_update_entity_registry(entity_id, new_name, timeout=10):
    log_path = '/data/irrigazione_ws_debug.log'
    opts = read_options()
    debug_enable = bool(opts.get('debug_ws') or opts.get('debug') or False)

    def _log(msg):
        if not debug_enable:
            return
        try:
            with open(log_path, 'a', encoding='utf-8') as _f:
                _f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    try:
        from websocket import create_connection
    except Exception as e:
        _log(f"import websocket failed: {e}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            from websocket import create_connection
        except Exception as e2:
            _log(f"pip install websocket-client failed: {e2}")
            _log(traceback.format_exc())
            return False

    try:
        if HA_BASE.startswith("http://"):
            ws_url = HA_BASE.replace("http://", "ws://")
        elif HA_BASE.startswith("https://"):
            ws_url = HA_BASE.replace("https://", "wss://")
        else:
            ws_url = HA_BASE
        if not ws_url.endswith("/api/websocket"):
            ws_url = ws_url.rstrip("/") + "/api/websocket"

        ws = create_connection(ws_url, timeout=timeout)
        ws.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
        resp = json.loads(ws.recv())
        if resp.get("type") != "auth_ok":
            try:
                ws.close()
            except Exception:
                pass
            return False

        ws.send(json.dumps({"id": 1, "type": "entity_registry/update", "entity_id": entity_id, "name": new_name}))
        r = json.loads(ws.recv())
        try:
            ws.close()
        except Exception:
            pass
        return r.get("success") is True or "error" not in r
    except Exception:
        return False


@app.route('/api/irrigazione/zone/rename_ws', methods=['POST'])
def zone_rename_ws():
    data = request.get_json(silent=True) or {}
    entity_id = data.get('entity_id')
    new_name = data.get('name')
    zone_id = data.get('zone_id')
    base_minutes = data.get('base_minutes')
    ignore_weather = data.get('ignore_weather')

    if not entity_id and zone_id is None:
        return jsonify({
        "version": VERSION,'error': 'entity_id o zone_id richiesto'}), 400

    diagnostics = {'service_called': False, 'service_ok': None, 'service_error': None,
                   'tried_ws': False, 'ws_result': None}

    # try integration service e_dry.update_zone if possible
    try:
        bind = read_options().get('bind_config_entry_id')
        zones = discover_zones(strict_config_entry=bind)
        found = next((z for z in zones if z.get('switch') == entity_id), None)
        zone_id = found.get('id') if found else data.get('zone_id')
    except Exception:
        zone_id = data.get('zone_id')

    if zone_id:
        try:
            diagnostics['service_called'] = True
            payload = {'zone_id': zone_id, 'name': new_name}
            if base_minutes is not None:
                payload['base_minutes'] = base_minutes
            if ignore_weather is not None:
                payload['ignore_weather'] = ignore_weather
            if entity_id:
                payload['entity_id'] = entity_id
            ha_call_service('e_dry', 'update_zone', payload)
            diagnostics['service_ok'] = True
            _write_name_override(entity_id, new_name, zone_id=zone_id)
            return jsonify({
        "version": VERSION,'ok': True, 'entity_id': entity_id, 'zone_id': zone_id, 'name': new_name,
                            'updated_registry': True, 'via_service': True, 'diagnostics': diagnostics})
        except Exception as e:
            diagnostics['service_ok'] = False
            diagnostics['service_error'] = str(e)

    try:
        diagnostics['tried_ws'] = True
        ok_ws = ws_update_entity_registry(entity_id, new_name)
        diagnostics['ws_result'] = bool(ok_ws)
    except Exception:
        diagnostics['tried_ws'] = True
        diagnostics['ws_result'] = False

    if diagnostics.get('ws_result'):
        _write_name_override(entity_id, new_name, zone_id=zone_id)
        return jsonify({
        "version": VERSION,'ok': True, 'entity_id': entity_id, 'zone_id': zone_id, 'name': new_name,
                        'updated_registry': True, 'via_service': False, 'diagnostics': diagnostics})

    ok = _write_name_override(entity_id, new_name, zone_id=zone_id)
    if not ok:
        return jsonify({
        "version": VERSION,'error': 'impossibile salvare override nome'}), 500
    return jsonify({
        "version": VERSION,'ok': True, 'entity_id': entity_id, 'zone_id': zone_id, 'name': new_name,
                    'updated_registry': False, 'diagnostics': diagnostics})


# -------------------- METEO e-SunMind --------------------
def _is_valid_weather_value(value):
    return value is not None and str(value).strip().lower() not in ("", "unknown", "unavailable", "none", "nan")


def _add_weather_value(out, key, entity_id, value, unit=""):
    if _is_valid_weather_value(value):
        out[key] = {"entity_id": entity_id, "state": value, "unit": unit}


def _pack_weather_from_esunmind_payload(payload):
    payload = payload if isinstance(payload, dict) else {}
    source = payload.get("source")
    out = {
        "source": "e-SunMind",
        "ok": bool(payload.get("available", True)),
        "weather_source": source,
        "age_seconds": payload.get("age_seconds"),
        "last_update": payload.get("last_update"),
        "schema": payload.get("schema"),
    }
    _add_weather_value(out, "temperature", "sensor.e_sunmind_irrigation_temperature_c", payload.get("temperature_c"), "°C")
    _add_weather_value(out, "humidity", "sensor.e_sunmind_irrigation_humidity_pct", payload.get("humidity_pct"), "%")
    _add_weather_value(out, "pressure", "sensor.e_sunmind_irrigation_pressure_hpa", payload.get("pressure_hpa"), "hPa")
    _add_weather_value(out, "wind_speed", "sensor.e_sunmind_irrigation_wind_speed_ms", payload.get("wind_speed_ms"), "m/s")
    _add_weather_value(out, "rain_rate", "sensor.e_sunmind_irrigation_rain_rate_mm_h", payload.get("rain_rate_mm_h"), "mm/h")
    _add_weather_value(out, "rain_24h", "sensor.e_sunmind_irrigation_rain_last_24h_mm", payload.get("rain_last_24h_mm"), "mm")
    _add_weather_value(out, "forecast_rain_24h", "sensor.e_sunmind_irrigation_forecast_rain_24h_mm", payload.get("forecast_rain_24h_mm"), "mm")

    cond = payload.get("condition") or payload.get("weather_code") or payload.get("irrigation_weather_reason") or payload.get("error")
    if _is_valid_weather_value(cond):
        out["condition"] = {"entity_id": "e_sunmind.weather_irrigation", "state": str(cond)}

    out["guard"] = {
        "ok": bool(payload.get("available", False)),
        "is_raining": bool(payload.get("is_raining")),
        "rain_alarm": bool(payload.get("rain_block")),
        "wind_alarm": bool(payload.get("wind_block")),
        "freeze_block": bool(payload.get("freeze_block")),
        "hot_day": bool(payload.get("hot_day")),
        "dry_day": bool(payload.get("dry_day")),
        "score": payload.get("irrigation_weather_score"),
        "reason": payload.get("irrigation_weather_reason"),
        "station_used": source == "local_station",
    }
    return out


def _resolve_esunmind_weather_url(opts):
    url = str(opts.get("e_sunmind_api_url") or DEFAULT_ESUNMIND_API_URL).strip()
    if url.endswith("/api/data"):
        return url[:-len("/api/data")] + "/api/weather/irrigation"
    return url


def _fetch_esunmind_weather(opts):
    url = _resolve_esunmind_weather_url(opts)
    if not url:
        return None
    try:
        r = requests.get(url, timeout=8)
        if r.status_code >= 400:
            return {"error": "e_sunmind_http_error", "status": r.status_code, "url": url}
        payload = r.json() if r.text else {}
        out = _pack_weather_from_esunmind_payload(payload if isinstance(payload, dict) else {})
        out["url"] = url
        return out
    except Exception as e:
        return {"error": "e_sunmind_request_failed", "detail": str(e), "url": url}


def _weather_from_esunmind_entities():
    out = {"source": "e-SunMind HA sensors"}
    sensor_map = {
        "temperature": ("sensor.e_sunmind_weather_temp_c", "°C"),
        "humidity": ("sensor.e_sunmind_weather_humidity_pct", "%"),
        "pressure": ("sensor.e_sunmind_weather_pressure_hpa", "hPa"),
        "wind_speed": ("sensor.e_sunmind_weather_wind_ms", "m/s"),
        "rain_1h": ("sensor.e_sunmind_weather_precip_1h_mm", "mm"),
    }
    for key, (eid, fallback_unit) in sensor_map.items():
        st = ha_try_get_state(eid)
        if not st:
            continue
        attrs = st.get("attributes") or {}
        _add_weather_value(out, key, eid, st.get("state"), attrs.get("unit_of_measurement") or fallback_unit)
    return out if any(k in out for k in sensor_map) else None


# -------------------- METEO endpoint --------------------
@app.route('/api/device_weather')
def api_device_weather():
    ok, err = _require_token()
    if not ok:
        return err

    opts = read_options()
    out = _fetch_esunmind_weather(opts)
    if out and not out.get("error") and any(k in out for k in ("temperature", "humidity", "pressure", "wind_speed", "rain_1h")):
        return jsonify(out)

    fallback = _weather_from_esunmind_entities()
    if fallback:
        if out and out.get("error"):
            fallback["api_error"] = out
        return jsonify(fallback)

    return jsonify({"version": VERSION, "error": "e_sunmind_weather_not_found", "api": out}), 200


# --- Event log (read-only) ---
@app.route('/api/event_log')
def api_event_log():
    ok, err = _require_token()
    if not ok:
        return err

    entity_id = request.args.get('entity_id') or EVENT_LOG_ENTITY
    try:
        st = ha_get_state(entity_id)
    except Exception:
        st = None

    if not st:
        return jsonify({"version": VERSION, "ok": False, "entity_id": entity_id, "events": []}), 200

    attrs = st.get("attributes") or {}
    events = attrs.get("events") or attrs.get("event_log") or attrs.get("log") or attrs.get("items") or []
    if isinstance(events, str):
        try:
            events = json.loads(events)
        except Exception:
            events = []
    if not isinstance(events, list):
        events = []

    return jsonify({
        "version": VERSION,
        "ok": True,
        "entity_id": entity_id,
        "state": st.get("state"),
        "events": events,
    })

# Keep options endpoint (per la UI/index)
@app.route('/api/options')
def api_options():
    try:
        return jsonify(read_options())
    except Exception as e:
        return jsonify({
        "version": VERSION,'error': 'options_read_failed', 'detail': str(e)}), 500


if __name__ == '__main__':
    # support ingress/override via env
    port_env = os.environ.get("INGRESS_PORT") or os.environ.get("PORT") or "1977"
    try:
        port = int(str(port_env))
    except Exception:
        port = 1977
    print(f"[Irrigazione] Flask listen port={port} (INGRESS_PORT={os.environ.get('INGRESS_PORT')}, PORT={os.environ.get('PORT')})")
    app.run(host='0.0.0.0', port=port)


























