#!/usr/bin/env python3
"""
Entities debug server for Irrigazione Dashboard (port 1978)

Provides a simple UI backend used by `entities_index.html`.
Supports `?config_entry=...` to prefer registry-bound entities via HA template API
and a `debug=1` flag to return some diagnostics.

Reads `/data/zone_names.json` to apply name overrides saved by the dashboard.
"""
import os
import json
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import requests

app = Flask(__name__)
VERSION = "2.0.1"
HERE = Path(__file__).resolve().parent
INDEX_HTML = HERE / "entities_index.html"

HA_BASE = os.environ.get("HA_BASE", "http://supervisor/core")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "Content-Type": "application/json"}

def _extract_zone_id(attrs):
    """Best-effort zone id from attributes."""
    try:
        for key in ("zone_id", "zone", "irrigation_zone", "id_zona"):
            if key in (attrs or {}):
                val = attrs.get(key)
                try:
                    return int(val)
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _domain_of(entity_id: str) -> str:
    if not entity_id or "." not in entity_id:
        return ""
    return entity_id.split(".", 1)[0]


def read_options():
    try:
        with open('/data/options.json','r',encoding='utf-8') as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _read_name_overrides():
    try:
        with open('/data/zone_names.json','r',encoding='utf-8') as f:
            return json.load(f) or {}
    except Exception:
        return {}


def resolve_entities_by_config_entry(config_entry):
    if not SUPERVISOR_TOKEN:
        return []
    safe_ce = str(config_entry).replace("'","\\'")
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
    try:
        r = requests.post(f"{HA_BASE}/api/template", headers=HEADERS, json={"template": template}, timeout=30)
        if r.status_code >= 400:
            return []
        return json.loads(r.text)
    except Exception:
        return []


def _ha_require_token():
    if not SUPERVISOR_TOKEN:
        return False, jsonify({'error': 'missing_supervisor_token'}), 500
    return True, None


def ha_call_service(domain, service, payload):
    ok, resp = _ha_require_token()
    if not ok:
        # resp is (jsonify(...), status)
        raise RuntimeError('missing supervisor token')
    r = requests.post(f"{HA_BASE}/api/services/{domain}/{service}", headers=HEADERS, json=payload, timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"service call failed: {r.status_code} {r.text[:400]}")
    try:
        return r.json() if r.text else {'ok': True}
    except Exception:
        return {'ok': True}

def ha_get_state(entity_id: str):
    ok, resp = _ha_require_token()
    if not ok:
        return None
    try:
        r = requests.get(f"{HA_BASE}/api/states/{entity_id}", headers=HEADERS, timeout=20)
        if r.status_code >= 400:
            return None
        return r.json()
    except Exception:
        return None


def ha_entity_registry_list():
    """Return Home Assistant entity registry list (best-effort)."""
    ok, _ = _ha_require_token()
    if not ok:
        return []
    try:
        r = requests.get(f"{HA_BASE}/api/config/entity_registry/list", headers=HEADERS, timeout=30)
        if r.status_code >= 400:
            return []
        return r.json() or []
    except Exception:
        return []


@app.route('/')
def index():
    if not INDEX_HTML.exists():
        return jsonify({'error':'entities_index_missing','detail': str(INDEX_HTML)}), 500
    return send_file(str(INDEX_HTML))


@app.route('/entities')
@app.route('/entities.html')
def entities_page():
    # Backwards-compatible path used previously by the UI
    if not INDEX_HTML.exists():
        return jsonify({'error':'entities_index_missing','detail': str(INDEX_HTML)}), 500
    return send_file(str(INDEX_HTML))


@app.route('/api/entities')
def api_entities():
    opts = read_options()
    config_entry = request.args.get('config_entry') or opts.get('bind_config_entry_id')
    debug = request.args.get('debug') in ('1','true','True')

    overrides = _read_name_overrides()

    def _apply_override(eid, attrs):
        aa = dict(attrs or {})
        if eid in overrides:
            aa['friendly_name'] = overrides[eid]
            return aa
        zid = _extract_zone_id(attrs or {})
        if zid is not None and f"zone:{zid}" in overrides:
            aa['friendly_name'] = overrides[f"zone:{zid}"]
            return aa
        return attrs or {}

    # Prefer registry/template resolution when config_entry is provided
    if config_entry:
        entities = resolve_entities_by_config_entry(config_entry) or []
        filtered = []
        for e in entities:
            if not isinstance(e, dict):
                continue
            eid = e.get('entity_id')
            if not eid:
                continue
            attrs = _apply_override(eid, e.get('attributes') or {})
            filtered.append({'entity_id': eid, 'state': e.get('state'), 'attributes': attrs})

        out = {'entities': filtered, 'filtered_count': len(filtered), 'resolved_count': len(filtered)}

        if debug and len(filtered) == 0:
            # include raw template response for troubleshooting
            try:
                safe_ce = str(config_entry).replace("'","\\'")
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
                r = requests.post(f"{HA_BASE}/api/template", headers=HEADERS, json={'template': template}, timeout=30)
                out['template_status'] = r.status_code
                out['template_raw'] = (r.text or '')[:10000]
            except Exception as e:
                out['template_error'] = str(e)
        return jsonify(out)

    # Fallback: all states
    try:
        if not SUPERVISOR_TOKEN:
            return jsonify({'error':'missing_supervisor_token'}), 500
        r = requests.get(f"{HA_BASE}/api/states", headers=HEADERS, timeout=30)
        r.raise_for_status()
        all_states = r.json()
    except Exception as e:
        return jsonify({'error':'ha_request_failed','detail': str(e)}), 500

    out_list = []
    for s in all_states:
        eid = s.get('entity_id')
        if not eid:
            continue
        attrs = _apply_override(eid, s.get('attributes') or {})
        out_list.append({'entity_id': eid, 'state': s.get('state'), 'attributes': attrs})

    if debug:
        return jsonify({'entities': out_list, 'resolved_count': len(out_list), 'filtered_count': len(out_list), 'debug': 'all_states'})
    return jsonify(out_list)

@app.route('/api/entities_grouped')
def api_entities_grouped():
    """Return entities grouped by detected zone number for diagnostics.

    Query params:
      - config_entry: use registry/template to resolve entities bound to the config entry
      - entry_id: optional short entry id used in unique_id patterns (helps detection)
    """
    opts = read_options()
    config_entry = request.args.get('config_entry') or opts.get('bind_config_entry_id')
    entry_id = request.args.get('entry_id')
    debug = request.args.get('debug') in ('1','true','True')

    zones_info_entity = opts.get('zones_info_entity') or 'sensor.e_dry_zones_info'
    programs_info_entity = opts.get('programs_info_entity') or 'sensor.e_dry_programs_info'
    meteo_info_entity = opts.get('meteo_info_entity') or 'sensor.e_dry_meteo_info'
    programs_enabled_entity = opts.get('programs_enabled_entity') or 'switch.programmi_abilitati'

    entities = []
    if config_entry:
        entities = resolve_entities_by_config_entry(config_entry)
    else:
        try:
            r = requests.get(f"{HA_BASE}/api/states", headers=HEADERS, timeout=30)
            r.raise_for_status()
            entities = r.json()
        except Exception as e:
            return jsonify({'error':'ha_request_failed','detail': str(e)}), 500

    # Build lookup by entity_id and simplified records
    recs = {}
    for e in entities:
        if not isinstance(e, dict):
            continue
        eid = e.get('entity_id')
        if not eid:
            continue
        attrs = e.get('attributes') or {}
        recs[eid] = {'entity_id': eid, 'name': attrs.get('friendly_name') or attrs.get('name') or '', 'unique_id': attrs.get('unique_id'), 'state': e.get('state'), 'attributes': attrs}

    # Entity registry is used to resolve entities that are not bound to the config entry
    registry = ha_entity_registry_list()

    def _as_ent(entity_id: str):
        """Return a normalized entity row for UI (entity_id, state, name, attributes)."""
        r = recs.get(entity_id)
        if r:
            return {'entity_id': r.get('entity_id'), 'state': r.get('state'), 'name': r.get('name') or '', 'attributes': r.get('attributes') or {}}
        st = ha_get_state(entity_id)
        if not st:
            return None
        attrs = st.get('attributes') or {}
        return {'entity_id': entity_id, 'state': st.get('state'), 'name': attrs.get('friendly_name') or attrs.get('name') or '', 'attributes': attrs}

    # Aggregated sensors + main switch
    aggregates = []
    for eid in (zones_info_entity, programs_info_entity, meteo_info_entity, programs_enabled_entity):
        ent = _as_ent(eid)
        if ent:
            aggregates.append(ent)

    def _ensure_entity(entity_id: str):
        """Ensure entity exists in `recs` even if outside the config entry."""
        if not entity_id:
            return None
        if entity_id in recs:
            return recs[entity_id]
        st = ha_get_state(entity_id)
        if not st:
            return None
        attrs = st.get('attributes') or {}
        recs[entity_id] = {
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or attrs.get('name') or '',
            'unique_id': attrs.get('unique_id'),
            'state': st.get('state'),
            'attributes': attrs,
        }
        return recs[entity_id]

    # Collect referenced entities for richer debugging
    references = {'meteo': [], 'physical_switches': []}

    # Meteo refs from the aggregated meteo sensor
    m_info = _as_ent(meteo_info_entity)
    if m_info:
        m_attrs = m_info.get('attributes') or {}
        for k in ('weather_entity', 'rain_sensor', 'temp_sensor', 'hum_sensor', 'wind_sensor'):
            ref = m_attrs.get(k)
            if isinstance(ref, str) and '.' in ref:
                rr = _ensure_entity(ref)
                if rr and rr not in references['meteo']:
                    references['meteo'].append(rr)

    # Authoritative zone list from the aggregated sensor zones_info
    zones_def = None
    z_info = _as_ent(zones_info_entity)
    if z_info:
        attrs = z_info.get('attributes') or {}
        if isinstance(attrs.get('zones'), list):
            zones_def = attrs.get('zones')

    groups_out = {}
    unassigned = []
    programs = []
    program_groups_out = {}

    import re

    if zones_def:
        # zones_def is list of dicts with id,name and switch_entity_id (physical)
        for z in zones_def:
            zid = z.get('id')
            zname = z.get('name') or z.get('zone_name') or ''
            zprefix = z.get('unique_id_prefix') or ''
            phys = z.get('switch_entity_id') or z.get('physical_switch') or z.get('switch')
            group_members = []
            # collect matches: prefer physical switch
            if phys:
                r_phys = recs.get(phys) or _ensure_entity(phys)
                if r_phys:
                    group_members.append(r_phys)
                    if r_phys not in references['physical_switches']:
                        references['physical_switches'].append(r_phys)

            # Pull all entities from registry matching the zone unique_id prefix (most reliable mapping)
            if zprefix:
                for er in (registry or []):
                    try:
                        if str(er.get('unique_id') or '').startswith(str(zprefix)):
                            rr = _ensure_entity(er.get('entity_id'))
                            if rr and rr not in group_members:
                                group_members.append(rr)
                    except Exception:
                        continue

            # Probe common naming patterns as extra fallback (esp. for customized entity_id)
            if zid is not None:
                zid_s = str(zid)
                probe = []
                # ignore meteo (zone 1 sometimes has no suffix)
                probe += [f"switch.ignora_meteo_{zid_s}", f"input_boolean.ignora_meteo_{zid_s}", f"switch.ignore_meteo_{zid_s}", f"input_boolean.ignore_meteo_{zid_s}"]
                if str(zid_s) == "1":
                    probe += ["switch.ignora_meteo", "input_boolean.ignora_meteo", "switch.ignore_meteo", "input_boolean.ignore_meteo"]
                # duration slider
                probe += [f"number.zona_{zid_s}_durata", f"number.{zid_s}_durata", f"input_number.zona_{zid_s}_durata", f"input_number.{zid_s}_durata"]
                # configured duration
                probe += [f"sensor.zona_{zid_s}_durata_configurata", f"sensor.{zid_s}_durata_configurata", f"sensor.centralina_irrigazione_zona_{zid_s}_durata_configurata"]
                # remaining
                probe += [f"sensor.zona_{zid_s}_remaining", f"sensor.{zid_s}_remaining", f"sensor.centralina_irrigazione_zona_{zid_s}_remaining"]
                # progress
                probe += [f"sensor.zona_{zid_s}_progresso", f"sensor.{zid_s}_progresso", f"sensor.centralina_irrigazione_zona_{zid_s}_progresso"]
                # smart/effective (best-effort patterns)
                probe += [f"sensor.zona_{zid_s}_durata_smart", f"sensor.zona_{zid_s}_durata_meteo", f"sensor.zona_{zid_s}_durata_effettiva"]

                for eid in probe:
                    rr = _ensure_entity(eid)
                    if rr and rr not in group_members:
                        group_members.append(rr)
            # include any rec with explicit zone_id attribute matching zid
            for r in recs.values():
                attrs = r.get('attributes') or {}
                zid_attr = _extract_zone_id(attrs)
                if zid_attr is not None and zid is not None and str(zid_attr) == str(zid):
                    if r not in group_members:
                        group_members.append(r)
            # then find by friendly_name containing zone name
            lname = (zname or '').strip().lower()
            for r in recs.values():
                if r['entity_id'] == phys:
                    continue
                rn = (r.get('name') or '').lower()
                if lname and lname in rn:
                    if r not in group_members:
                        group_members.append(r)
            # finally, fallback: look for entity_id patterns with zone id
            if zid is not None:
                for r in recs.values():
                    eid = r['entity_id']
                    if eid == phys:
                        continue
                    if re.search(rf'\b{zid}\b', eid) or re.search(rf'[_\.-]{zid}\b', eid):
                        if r not in group_members:
                            group_members.append(r)

            # build role mapping for expected 7 entities
            role_map = {'switch': None, 'slider_duration': None, 'configured_duration': None, 'smart_duration': None, 'effective_duration': None, 'remaining': None, 'progress': None, 'ignore_meteo': None}
            for r in group_members:
                eid = (r.get('entity_id') or '')
                n = (r.get('name') or '').lower()
                leid = eid.lower()
                dom = _domain_of(eid).lower()
                # switch (prefer exact physical switch or conventional names)
                if phys and eid == phys:
                    role_map['switch'] = r
                    continue
                if dom == 'switch' or leid.startswith('switch.zona_') or n.strip() == (zname or '').strip().lower():
                    if role_map['switch'] is None:
                        role_map['switch'] = r
                        continue

                # configured duration (prefer explicit "configurata")
                if 'durata_configurata' in leid or 'durata configurata' in n or 'durata_configurata' in n:
                    role_map['configured_duration'] = r
                    continue

                # smart / meteo duration
                if 'durata_smart' in leid or 'durata_meteo' in leid or 'durata meteo' in n or 'meteo' in n:
                    role_map['smart_duration'] = r
                    continue

                # effective duration
                if 'durata_effettiva' in leid or 'durata effettiva' in n or 'effettiva' in n:
                    role_map['effective_duration'] = r
                    continue

                # remaining
                if 'remaining' in leid or 'remaining' in n or '_remaining' in leid or leid.endswith('_remaining'):
                    role_map['remaining'] = r
                    continue

                # progress
                if 'progresso' in n or 'progresso' in leid or 'progress' in n or '_progresso' in leid:
                    role_map['progress'] = r
                    continue

                # ignore meteo
                if dom in ('input_boolean','switch'):
                    if ('ignore' in leid or 'ignora' in leid or 'ignore' in n or 'ignora' in n) and ('meteo' in leid or 'weather' in leid or 'meteo' in n or 'weather' in n):
                        role_map['ignore_meteo'] = r
                        continue

                # slider duration: prefer number domain or entities explicitly containing 'durata' when nothing more specific matched
                if dom in ('number','input_number') and 'durata' in leid:
                    role_map['slider_duration'] = r
                    continue
                if 'durata' in n and role_map['slider_duration'] is None and role_map['configured_duration'] is None and role_map['effective_duration'] is None:
                    role_map['slider_duration'] = r
                    continue

            groups_out[str(zid)] = {'zone_name': zname, 'roles': role_map, 'members': [m['entity_id'] for m in group_members]}

        # any recs not assigned
        assigned_ids = set()
        for v in groups_out.values():
            for mid in v['members']:
                assigned_ids.add(mid)
        for eid, r in recs.items():
            if eid not in assigned_ids:
                unassigned.append(r)

        # Programs: use aggregated programs_info sensor when available
        p_info = _as_ent(programs_info_entity)
        p_list = []
        if p_info:
            attrs = p_info.get('attributes') or {}
            if isinstance(attrs.get('programs'), list):
                p_list = attrs.get('programs')

        def _extract_program_id_from_entity(r):
            attrs = r.get('attributes') or {}
            for key in ('program_id', 'program', 'id_programma', 'programma_id'):
                if key in attrs:
                    try:
                        return int(attrs.get(key))
                    except Exception:
                        pass
            # fallback: read from entity_id tokens
            eid = (r.get('entity_id') or '').lower()
            m = re.search(r'(?:program|programma)[ _-]?(\d{1,3})', eid)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return None
            return None

        # Build program groups using p_list ids, then attach matching entities
        for p in (p_list or []):
            try:
                pid = int(p.get('id'))
            except Exception:
                continue
            program_groups_out[str(pid)] = {
                'program_id': pid,
                'name': p.get('name') or '',
                'members': [],
            }

        # attach entities to program groups
        remaining = []
        for r in unassigned:
            pid = _extract_program_id_from_entity(r)
            if pid is not None and str(pid) in program_groups_out:
                program_groups_out[str(pid)]['members'].append(r)
            else:
                remaining.append(r)

        # Deduplicate and flatten program entities list
        seen = set()
        dedup_programs = []
        for g in program_groups_out.values():
            for r in g.get('members', []):
                eid = r.get('entity_id')
                if eid and eid not in seen:
                    dedup_programs.append(r)
                    seen.add(eid)

        payload = {
            'version': VERSION,
            'meta': {
                'config_entry': config_entry,
                'zones_info_entity': zones_info_entity,
                'programs_info_entity': programs_info_entity,
                'meteo_info_entity': meteo_info_entity,
                'programs_enabled_entity': programs_enabled_entity,
                'zones_def_count': len(zones_def or []),
                'programs_def_count': len(p_list or []),
            },
            'aggregates': aggregates,
            'references': references,
            'groups': groups_out,
            'program_groups': program_groups_out,
            'programs': dedup_programs,
            'unassigned': remaining,
        }
        if debug:
            payload['debug'] = {'total_entities': len(recs)}
        return jsonify(payload)

    # Fallback to previous grouping behavior when no zones_def present
    groups = {}
    unassigned = []
    for r in recs.values():
        uid = (r.get('unique_id') or '')
        eid = r.get('entity_id') or ''
        name = r.get('name') or ''
        found = None
        # Try patterns in unique_id first
        if uid:
            m = re.search(r'zone[_\-]?(\d{1,2})', uid, re.I)
            if not m and entry_id:
                m = re.search(re.escape(entry_id) + r'.*?_(\d{1,2})', uid, re.I)
            if m:
                found = int(m.group(1))
        # Try entity_id
        if found is None:
            m = re.search(r'zone[_\-]?(\d{1,2})', eid, re.I)
            if not m:
                m = re.search(r'_(\d{1,2})\b', eid)
            if m:
                found = int(m.group(1))
        # Try friendly name
        if found is None and name:
            m = re.search(r'zona\s*(\d{1,2})', name, re.I)
            if not m:
                m = re.search(r'\b(\d{1,2})\b', name)
            if m:
                found = int(m.group(1))

        if found is None:
            unassigned.append(r)
        else:
            groups.setdefault(str(found), []).append(r)

    out = {'groups': {}, 'unassigned': unassigned}
    for k in sorted(groups.keys(), key=lambda x: int(x)):
        out['groups'][k] = sorted(groups[k], key=lambda x: x.get('entity_id'))

    return jsonify(out)


@app.route('/api/entity/set', methods=['POST'])
def api_entity_set():
    """Generic endpoint used by the entities UI to control entities.

    Expected JSON body: { entity_id, domain, action, value }
    - domain may be omitted and inferred from entity_id
    - action is the service name (e.g. 'turn_on','turn_off','set_value','press','select_option')
    - value is used for set_value/select_option
    """
    data = request.get_json(silent=True) or {}
    entity_id = data.get('entity_id')
    domain = data.get('domain') or (entity_id.split('.',1)[0] if entity_id and '.' in entity_id else None)
    action = data.get('action')
    value = data.get('value')

    if not entity_id or not domain or not action:
        return jsonify({'error': 'entity_id, domain e action richiesti'}), 400

    try:
        # Map common actions to service calls
        svc = action
        payload = {'entity_id': entity_id}
        if action in ('turn_on','turn_off'):
            svc = action
        elif action in ('press',) and domain == 'button':
            svc = 'press'
        elif action in ('set_value',):
            svc = 'set_value'
            payload['value'] = value
        elif action in ('select_option',):
            svc = 'select_option'
            payload['option'] = value
        else:
            # Use provided action as service name and include value if present
            if value is not None:
                payload['value'] = value

        res = ha_call_service(domain, svc, payload)
        return jsonify({'ok': True, 'result': res})
    except Exception as e:
        return jsonify({'error': 'service_call_failed', 'detail': str(e)}), 500



@app.route('/api/device_weather')
def api_device_weather():
    """Return weather values.

    Works in two modes:
      1) If query param device_id is provided, tries to infer weather entities from that device.
      2) If device_id is missing, falls back to a weather.* entity (prefers weather.openweathermap if present).
    """
    device_id = request.args.get('device_id')

    ok, resp = _ha_require_token()
    if not ok:
        return resp

    # Helper to read a HA state object
    def _get_state(entity_id: str):
        rr = requests.get(f"{HA_BASE}/api/states/{entity_id}", headers=HEADERS, timeout=20)
        if rr.status_code >= 400:
            return None
        return rr.json()

    # --- Mode 2: no device_id (Ingress-friendly) ---
    if not device_id:
        # Prefer a well-known entity if present
        wx = _get_state('weather.openweathermap')
        if wx is None:
            # Discover first weather.* entity
            try:
                rr = requests.get(f"{HA_BASE}/api/states", headers=HEADERS, timeout=20)
                if rr.status_code < 400:
                    all_states = rr.json()
                    for st in all_states:
                        eid = st.get('entity_id', '')
                        if eid.startswith('weather.'):
                            wx = st
                            break
            except Exception:
                wx = None

        if wx is None:
            return jsonify({'error': 'weather_not_found'}), 404

        attrs = wx.get('attributes', {}) or {}
        def _num(x):
            try:
                return float(x)
            except Exception:
                return x

        payload = {
            'condition': {'entity_id': wx.get('entity_id'), 'state': wx.get('state')},
            'temperature': {'entity_id': wx.get('entity_id'), 'state': _num(attrs.get('temperature')), 'unit': attrs.get('temperature_unit') or '°C'},
            'humidity': {'entity_id': wx.get('entity_id'), 'state': _num(attrs.get('humidity')), 'unit': '%'},
            'pressure': {'entity_id': wx.get('entity_id'), 'state': _num(attrs.get('pressure')), 'unit': attrs.get('pressure_unit') or 'hPa'},
            'wind_speed': {'entity_id': wx.get('entity_id'), 'state': _num(attrs.get('wind_speed')), 'unit': attrs.get('wind_speed_unit') or 'km/h'},
        }
        return jsonify(payload)

    # --- Mode 1: device_id provided (legacy) ---
    try:
        r = requests.get(f"{HA_BASE}/api/devices/{device_id}/entities", headers=HEADERS, timeout=20)
        if r.status_code >= 400:
            return jsonify({'error': 'ha_request_failed', 'status': r.status_code, 'detail': r.text[:2000]}), 500
        entities = r.json()
    except Exception as e:
        return jsonify({'error': 'ha_request_failed', 'detail': str(e)}), 500

    # Keep the existing inference logic below (unchanged)

    out = {}
    def _set_key(k, val):
        if k not in out:
            out[k] = val

    for ent in entities:
        eid = ent.get('entity_id') or ent.get('id')
        if not eid:
            continue
        try:
            r = requests.get(f"{HA_BASE}/api/states/{eid}", headers=HEADERS, timeout=10)
            if r.status_code >= 400:
                continue
            s = r.json()
        except Exception:
            continue

        attrs = s.get('attributes') or {}
        dc = (attrs.get('device_class') or '').lower()
        lname = (eid or '').lower()
        unit = attrs.get('unit_of_measurement') or attrs.get('unit') or ''
        state = s.get('state')

        if dc == 'temperature' or 'temperature' in lname or lname.endswith('_temp') or 'temp' in lname:
            _set_key('temperature', {'entity_id': eid, 'state': state, 'unit': unit})
            continue
        if dc == 'humidity' or 'humidity' in lname:
            _set_key('humidity', {'entity_id': eid, 'state': state, 'unit': unit})
            continue
        if dc == 'pressure' or 'pressure' in lname:
            _set_key('pressure', {'entity_id': eid, 'state': state, 'unit': unit})
            continue
        if dc in ('wind_speed', 'speed') or 'wind' in lname:
            _set_key('wind_speed', {'entity_id': eid, 'state': state, 'unit': unit})
            continue
        if eid.startswith('weather.') or 'weather' in lname:
            _set_key('condition', {'entity_id': eid, 'state': state, 'attributes': attrs})
            continue

    return jsonify(out)

# --- merged options helper (runtime overrides repo config.yaml) ---
def read_options_merged():
    out = {}
    # runtime options persisted by the addon (supervisor options)
    try:
        with open('/data/options.json','r',encoding='utf-8') as f:
            opts = json.load(f) or {}
            if isinstance(opts, dict):
                out.update(opts)
    except Exception:
        pass

    # try reading repo-level config.yaml (fallback / documentation)
    try:
        cfg_path = HERE.parent.parent / 'config.yaml'
        if cfg_path.exists():
            try:
                import yaml
                with open(str(cfg_path),'r',encoding='utf-8') as f:
                    cfg = yaml.safe_load(f) or {}
                    if isinstance(cfg, dict):
                        for k,v in cfg.items():
                            if k not in out:
                                out[k] = v
            except Exception:
                try:
                    import re
                    with open(str(cfg_path),'r',encoding='utf-8') as f:
                        for line in f:
                            m = re.match(r"^\s*(owm_device_id|device_id)\s*:\s*(\S+)", line)
                            if m:
                                k = m.group(1)
                                v = m.group(2).strip().strip('"\'')
                                if k not in out:
                                    out[k] = v
                except Exception:
                    pass
    except Exception:
        pass
    return out

# make existing callers use the merged reader
read_options = read_options_merged

@app.route('/api/options')
def api_options():
    """Return merged options read by `read_options()`."""
    try:
        return jsonify(read_options())
    except Exception as e:
        return jsonify({'error': 'options_read_failed', 'detail': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('ENTITIES_PORT', os.environ.get('PORT', 1978)))
    app.run(host='0.0.0.0', port=port)
