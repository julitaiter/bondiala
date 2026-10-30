"""BA Data physical stops and conservative, auditable PostGIS associations.

No catalogue entities or ledger entries are deleted by this pipeline.
"""

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone

from transport.models import Linea, Parada, Recorrido, RecorridoParada, normalize_line
from .models import DataSource, ImportError, ImportRun, StopMatchIssue
from .services import geometry, load_document, validate_geojson

CATALOGUE_LOCK = 6132041


def normalized(value):
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return " ".join(
        re.sub(
            r"[^\w]+", " ", "".join(c for c in text if not unicodedata.combining(c))
        ).split()
    )


def key_name(value):
    return re.sub(r"[^a-z0-9]", "", normalized(value))


def text_value(props, names, max_length):
    value = next((props[n] for n in names if props.get(n) is not None), "")
    if isinstance(value, (dict, list, bool)):
        raise ValueError(f"Propiedad {names[0]} de tipo inválido.")
    value = " ".join(str(value).split())
    if len(value) > max_length:
        raise ValueError(f"Propiedad {names[0]} demasiado larga.")
    return value


def parse_stop(feature):
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise ValueError("Se esperaba Feature.")
    raw = feature.get("properties")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Faltan properties de la parada.")
    if len(json.dumps(raw, ensure_ascii=False)) > 20000:
        raise ValueError("Metadata de parada demasiado grande.")
    props = {key_name(k): v for k, v in raw.items()}
    try:
        point = geometry(feature.get("geometry"), "Point")
    except Exception as exc:
        raise ValueError("Point o coordenadas inválidos.") from exc
    street = text_value(props, ["calle", "street"], 200)
    height = text_value(props, ["altplano", "altura"], 30)
    address = text_value(props, ["direccion", "address"], 250) or " ".join(
        filter(None, [street, height])
    )
    if not address:
        raise ValueError("La identidad requiere una dirección o calle/altura.")
    identity = f"v1|{point.x:.6f}|{point.y:.6f}|{normalized(address)}"
    external = "coord-address-v1:" + hashlib.sha256(identity.encode()).hexdigest()
    services, problems = set(), []
    for slot in range(1, 7):
        line = props.get(f"l{slot}")
        if line is None or str(line).strip() == "":
            continue
        try:
            number = normalize_line(line)
        except ValueError:
            problems.append(f"L{slot}: línea no reconocible {str(line)[:30]!r}.")
            continue
        direction_raw = str(props.get(f"l{slot}sen") or "").strip().upper()
        direction = {"I": "IDA", "V": "VUELTA", "IDA": "IDA", "VUELTA": "VUELTA"}.get(
            direction_raw
        )
        if not direction:
            problems.append(
                f"L{slot}={number}: sentido {direction_raw[:20]!r} sin equivalencia documentada."
            )
            services.add((number, ""))
        else:
            services.add((number, direction))
    # Also accept equivalent field names in local developer fixtures.
    if not services and (props.get("linea") or props.get("line")):
        try:
            number = normalize_line(props.get("linea", props.get("line")))
            direction_raw = str(props.get("sentido", "")).strip().upper()
            direction = {
                "I": "IDA",
                "V": "VUELTA",
                "IDA": "IDA",
                "VUELTA": "VUELTA",
            }.get(direction_raw, "")
            services.add((number, direction))
            if not direction:
                problems.append("Sentido ausente o inválido.")
        except ValueError:
            problems.append("Línea no reconocible.")
    metadata = {
        "identity_version": "coord-address-v1",
        "calle": street,
        "altura": height,
        "lineas": [{"numero": n, "sentido": d} for n, d in sorted(services)],
        "origen": raw,
    }
    return (
        external,
        {
            "nombre": address,
            "direccion": address,
            "barrio": text_value(props, ["barrio"], 100),
            "comuna": text_value(props, ["comuna"], 30),
            "ubicacion": point,
            "es_oficial": True,
            "activa": True,
            "metadata": metadata,
        },
        problems,
    )


def issue(run, stop, reason, line="", direction="", candidates=None):
    StopMatchIssue.objects.create(
        run=run,
        parada=stop,
        reason=reason,
        linea=line,
        sentido=direction,
        candidates=candidates or [],
    )


def spatial_candidates(source_id, maximum):
    """One indexed candidate join, including ordered MultiLineString components.

    Geography gives meter distances/lengths; UTM 21S locates fractions in CABA.
    Never merge/reverse components (ST_LineMerge would change source ordering).
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
        WITH route_parts AS MATERIALIZED (
          SELECT r.id route_id,d.path[1] component,d.path[2] edge,d.geom part,
                 ST_Transform(d.geom,32721) projected,
                 ST_Length(d.geom::geography) length
          FROM transport_recorrido r CROSS JOIN LATERAL ST_DumpSegments(r.geometria) d
          WHERE r.geometria IS NOT NULL AND r.activo
        ), edges AS MATERIALIZED (
          SELECT *,COALESCE(SUM(length) OVER(PARTITION BY route_id ORDER BY component,edge
              ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),0) offset_meters
          FROM route_parts
        ), nearby AS (
          SELECT p.id stop_id, r.id route_id, l.numero, r.sentido, p.ubicacion,
                 ST_Transform(p.ubicacion,32721) projected_point,
                 ST_Envelope(ST_Buffer(p.ubicacion::geography,%s)::geometry) bounds
          FROM transport_parada p
          CROSS JOIN LATERAL jsonb_array_elements(COALESCE(p.metadata->'lineas', '[]'::jsonb)) s
          JOIN transport_linea l ON l.numero=s->>'numero' AND l.activa
          JOIN transport_ramal b ON b.linea_id=l.id AND b.activo
          JOIN transport_recorrido r ON r.ramal_id=b.id AND r.sentido=s->>'sentido' AND r.activo
          WHERE p.source_id=%s AND p.es_oficial AND p.activa AND r.geometria IS NOT NULL
            AND r.geometria && ST_Envelope(ST_Buffer(p.ubicacion::geography,%s)::geometry)
            AND ST_DWithin(r.geometria::geography,p.ubicacion::geography,%s)
        )
        SELECT n.stop_id,n.route_id,n.numero,n.sentido,
               ST_Distance(e.part::geography,n.ubicacion::geography) distance,
               e.offset_meters + ST_LineLocatePoint(e.projected,n.projected_point)*e.length position,
               e.component,e.edge
        FROM nearby n JOIN edges e ON e.route_id=n.route_id AND e.part && n.bounds
          AND ST_DWithin(e.part::geography,n.ubicacion::geography,%s)
        ORDER BY n.stop_id,n.route_id,distance,e.component,e.edge
        """,
            [maximum, source_id, maximum, maximum, maximum],
        )
        rows = cursor.fetchall()
    by_route = defaultdict(list)
    for stop, route, line, direction, distance, position, component, edge in rows:
        by_route[(stop, route, line, direction)].append(
            {
                "recorrido": route,
                "distancia_metros": round(distance, 4),
                "posicion_metros": round(position, 4),
                "componente": component,
                "segmento": edge,
            }
        )
    candidates = defaultdict(list)
    for (stop, route, line, direction), parts in by_route.items():
        first = parts[0]
        first["position_ambiguous"] = any(
            p["distancia_metros"] <= first["distancia_metros"] + 1
            and abs(p["posicion_metros"] - first["posicion_metros"]) > 10
            for p in parts[1:]
        )
        candidates[(stop, line, direction)].append(first)
    for values in candidates.values():
        values.sort(key=lambda c: (c["distancia_metros"], c["recorrido"]))
    return candidates


def migrate_progress(old, new, line):
    """Change progress identity only; immutable ledger and trip snapshots stay intact."""
    from trips.models import UsuarioLineaParada

    rows = UsuarioLineaParada.objects.filter(parada=old, linea=line).order_by("pk")
    for row in rows:
        target = UsuarioLineaParada.objects.filter(
            usuario_id=row.usuario_id, linea=line, parada=new
        ).first()
        if target:
            # Preserve earliest known passage when two identities already exist.
            if row.primera_fecha < target.primera_fecha:
                UsuarioLineaParada.objects.filter(pk=target.pk).update(
                    primera_fecha=row.primera_fecha, primer_viaje_id=row.primer_viaje_id
                )
            row.delete()
        else:
            UsuarioLineaParada.objects.filter(pk=row.pk).update(parada=new)


def reconcile(route, selected, existing, run, metrics):
    legacy = [x for x in existing if x.parada.es_ilustrativa]
    if not legacy or not selected:
        return {}
    maximum = settings.PARADA_RECONCILE_MAX_DISTANCE_METERS
    with connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT a.id,b.id,ST_Distance(a.ubicacion::geography,b.ubicacion::geography)
        FROM transport_parada a CROSS JOIN transport_parada b
        WHERE a.id=ANY(%s) AND b.id=ANY(%s)
          AND a.ubicacion && ST_Envelope(ST_Buffer(b.ubicacion::geography,%s)::geometry)
          AND ST_DWithin(a.ubicacion::geography,b.ubicacion::geography,%s)
        """,
            [[x.parada_id for x in legacy], list(selected), maximum, maximum],
        )
        pairs = cursor.fetchall()
    old_options, new_options = defaultdict(set), defaultdict(set)
    for old, new, _ in pairs:
        old_options[old].add(new)
        new_options[new].add(old)
    equivalents = {}
    repetitions = Counter(x.parada_id for x in legacy)
    proposed = []
    for occurrence in legacy:
        options = old_options[occurrence.parada_id]
        if len(options) == 1 and repetitions[occurrence.parada_id] == 1:
            new = next(iter(options))
            if len(new_options[new]) == 1:
                proposed.append((occurrence, new))
    # An inversion of legacy order is evidence against an automatic equivalence.
    positions = [
        selected[new]["posicion_metros"]
        for occ, new in sorted(proposed, key=lambda x: x[0].orden)
    ]
    if positions != sorted(positions):
        for occurrence, _ in proposed:
            issue(
                run,
                occurrence.parada,
                "legacy_order_conflict",
                route.ramal.linea.numero,
                route.sentido,
            )
        proposed = []
    existing_spatial = {x.parada_id: x for x in existing if x.metodo == "spatial"}
    for occurrence, new_id in proposed:
        old = occurrence.parada
        previous_map = old.metadata.get("official_equivalences", {})
        previous = previous_map.get(route.ramal.linea.numero)
        if previous and previous != new_id:
            issue(
                run,
                old,
                "legacy_identity_conflict",
                route.ramal.linea.numero,
                route.sentido,
            )
            continue
        new = Parada.objects.get(pk=new_id)
        migrate_progress(old, new, route.ramal.linea)
        old.metadata = {
            **old.metadata,
            "legacy": True,
            "official_equivalences": {**previous_map, route.ramal.linea.numero: new_id},
        }
        old.save(update_fields=["metadata", "updated_at"])
        occurrence.parada = new
        if new_id in existing_spatial and existing_spatial[new_id].pk != occurrence.pk:
            occurrence.activa = False
            occurrence.metodo = "legacy"
        occurrence.save(update_fields=["parada", "activa", "metodo"])
        equivalents[new_id] = occurrence
        metrics["paradas_ilustrativas_reconciliadas"] += 1
    return equivalents


def match_routes(source, run, metrics):
    maximum = settings.PARADA_MATCH_MAX_DISTANCE_METERS
    margin = settings.PARADA_MATCH_MIN_MARGIN_METERS
    if (
        not math.isfinite(maximum)
        or not 0 < maximum <= 500
        or not math.isfinite(margin)
        or not 0 <= margin <= maximum
    ):
        raise ValueError(
            "Umbral espacial inválido: distancia (0,500], margen [0,distancia]."
        )
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [CATALOGUE_LOCK])
    routes = list(
        Recorrido.objects.select_for_update()
        .select_related("ramal__linea")
        .filter(activo=True, ramal__activo=True, ramal__linea__activa=True)
    )
    route_ids = defaultdict(list)
    routes_by_id = {r.pk: r for r in routes}
    for route in routes:
        route_ids[(route.ramal.linea.numero, route.sentido)].append(route)
    StopMatchIssue.objects.filter(parada__source=source, status="pending").update(
        status="resolved"
    )
    candidates = spatial_candidates(source.pk, maximum)
    selected = defaultdict(dict)
    recognized = set(Linea.objects.filter(activa=True).values_list("numero", flat=True))
    no_candidate_stops = set()
    for stop in Parada.objects.filter(
        source=source, es_oficial=True, activa=True
    ).iterator():
        services = stop.metadata.get("lineas", [])
        if not any(s["numero"] in recognized for s in services):
            metrics["paradas_sin_linea_reconocida"] += 1
        for service in services:
            line, direction = service["numero"], service["sentido"]
            if line not in recognized:
                issue(run, stop, "unknown_line", line, direction)
                continue
            if not direction:
                issue(run, stop, "unknown_direction", line)
                continue
            options = candidates.get((stop.pk, line, direction), [])
            if not options:
                possible = route_ids.get((line, direction), [])
                reason = (
                    "no_geometry"
                    if possible and not any(r.geometria for r in possible)
                    else "outside_threshold" if possible else "no_route"
                )
                issue(
                    run,
                    stop,
                    reason,
                    line,
                    direction,
                    [
                        {"recorrido": r.pk, "tiene_geometria": bool(r.geometria)}
                        for r in possible
                    ],
                )
                no_candidate_stops.add(stop.pk)
                continue
            if options[0]["position_ambiguous"]:
                issue(run, stop, "ambiguous_position", line, direction, options)
                metrics["asociaciones_ambiguas"] += 1
                continue
            if (
                len(options) > 1
                and options[1]["distancia_metros"] - options[0]["distancia_metros"]
                < margin
            ):
                issue(run, stop, "ambiguous_branches", line, direction, options)
                metrics["asociaciones_ambiguas"] += 1
                continue
            chosen = options[0]
            selected[chosen["recorrido"]][stop.pk] = chosen
    metrics["paradas_sin_recorrido_candidato"] = len(no_candidate_stops)
    # Re-evaluate routes which previously had spatial links as well as new matches.
    affected = set(selected) | set(
        RecorridoParada.objects.filter(source=source, metodo="spatial").values_list(
            "recorrido_id", flat=True
        )
    )
    for route_id in sorted(affected):
        route = routes_by_id.get(route_id)
        if route is None:
            continue
        wanted = selected.get(route_id, {})
        existing = list(
            route.secuencia.select_related("parada__source").order_by("orden")
        )
        replacements = reconcile(route, wanted, existing, run, metrics)
        by_stop = {x.parada_id: x for x in existing if x.metodo == "spatial"}
        active_official = []
        for stop_id, match in sorted(
            wanted.items(), key=lambda item: (item[1]["posicion_metros"], item[0])
        ):
            occurrence = by_stop.get(stop_id) or replacements.get(stop_id)
            if occurrence is None:
                occurrence = RecorridoParada(recorrido=route, parada_id=stop_id)
                metrics["asociaciones_creadas"] += 1
            else:
                metrics["asociaciones_actualizadas"] += int(
                    not occurrence.activa
                    or occurrence.posicion_metros != match["posicion_metros"]
                    or occurrence.distancia_metros != match["distancia_metros"]
                    or occurrence.metodo != "spatial"
                )
            occurrence.activa = True
            occurrence.metodo = "spatial"
            occurrence.source = source
            occurrence.distancia_metros = match["distancia_metros"]
            occurrence.posicion_metros = match["posicion_metros"]
            active_official.append(occurrence)
        active_pks = {x.pk for x in active_official if x.pk}
        remainder = [x for x in existing if x.pk not in active_pks]
        for occurrence in remainder:
            if occurrence.metodo == "spatial" and occurrence.source_id == source.pk:
                occurrence.activa = False
            if occurrence.parada.es_ilustrativa and len(active_official) >= 2:
                occurrence.activa = False
                occurrence.metodo = "legacy"
                occurrence.parada.metadata = {
                    **occurrence.parada.metadata,
                    "legacy": True,
                }
                occurrence.parada.save(update_fields=["metadata", "updated_at"])
                metrics["paradas_legacy_conservadas"] += 1
                issue(
                    run,
                    occurrence.parada,
                    "legacy_unresolved",
                    route.ramal.linea.numero,
                    route.sentido,
                )
        # Vacate all existing positions first; preserve every occurrence primary key.
        offset = (
            max([x.orden for x in existing] or [0])
            + len(active_official)
            + len(existing)
            + 1
        )
        if existing:
            route.secuencia.update(orden=F("orden") + offset)
        for order, occurrence in enumerate(active_official + remainder, 1):
            occurrence.orden = order
            occurrence.save()
    return metrics


def coverage(metrics):
    routes = Recorrido.objects.filter(
        activo=True, ramal__activo=True, ramal__linea__activa=True
    )
    total = routes.count()
    geometry_count = routes.exclude(geometria=None).count()
    from django.db.models import Count

    counts = list(
        RecorridoParada.objects.filter(
            recorrido__in=routes,
            activa=True,
            parada__es_oficial=True,
            parada__activa=True,
        )
        .values("recorrido_id")
        .annotate(n=Count("pk"))
        .values_list("n", flat=True)
    )
    usable = (
        RecorridoParada.objects.filter(
            recorrido__in=routes.exclude(geometria=None),
            activa=True,
            parada__es_oficial=True,
            parada__activa=True,
        )
        .values("recorrido_id")
        .annotate(n=Count("pk"))
        .filter(n__gte=2)
        .count()
    )
    metrics.update(
        {
            "recorridos_totales": total,
            "recorridos_con_geometria": geometry_count,
            "recorridos_sin_geometria": total - geometry_count,
            "recorridos_con_parada_oficial": len(counts),
            "recorridos_con_secuencia_utilizable": usable,
            "cobertura_geometria_pct": (
                round(100 * geometry_count / total, 2) if total else 0
            ),
            "cobertura_paradas_pct": (
                round(100 * len(counts) / total, 2) if total else 0
            ),
            "cobertura_secuencia_pct": round(100 * usable / total, 2) if total else 0,
        }
    )


def import_official_stops(
    location,
    source_slug="badata-paradas",
    force=False,
    match=False,
    rematch=False,
    dry_run=False,
):
    metrics = {
        name: 0
        for name in [
            "features_leidas",
            "paradas_oficiales_leidas",
            "duplicados_fisicos",
            "paradas_sin_linea_reconocida",
            "asociaciones_creadas",
            "asociaciones_actualizadas",
            "asociaciones_ambiguas",
            "paradas_sin_recorrido_candidato",
            "paradas_ilustrativas_reconciliadas",
            "paradas_legacy_conservadas",
            "advertencias_servicios",
        ]
    }
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [CATALOGUE_LOCK])
            source, _ = DataSource.objects.get_or_create(
                slug=source_slug,
                defaults={
                    "nombre": "BA Data · Paradas oficiales",
                    "url": settings.BA_DATA_PARADAS_GEOJSON_URL,
                },
            )
            run = ImportRun.objects.create(
                source=source, kind="paradas_oficiales", location=str(location)[:1000]
            )
            if rematch:
                previous = (
                    source.runs.exclude(pk=run.pk)
                    .filter(kind="paradas_oficiales", status__in=["SUCCESS", "PARTIAL"])
                    .order_by("-pk")
                    .first()
                )
                run.checksum = previous.checksum if previous else ""
                metrics["paradas_oficiales_leidas"] = source.parada_set.filter(
                    es_oficial=True
                ).count()
            else:
                document, run.checksum = load_document(location)
                validate_geojson(document)
                metrics["features_leidas"] = len(document["features"])
                previous = (
                    source.runs.exclude(pk=run.pk)
                    .filter(kind="paradas_oficiales", status__in=["SUCCESS", "PARTIAL"])
                    .order_by("-pk")
                    .first()
                )
                # A prior import-only run must not skip a newly requested matching phase.
                unchanged = (
                    previous
                    and previous.status == "SUCCESS"
                    and previous.checksum == run.checksum
                    and (not match or previous.metrics.get("matching_done"))
                )
                if unchanged and not force:
                    run.status = "UNCHANGED"
                    run.skipped = metrics["features_leidas"]
                    metrics["paradas_oficiales_leidas"] = source.parada_set.filter(
                        es_oficial=True
                    ).count()
                else:
                    unique = {}
                    for index, feature in enumerate(document["features"]):
                        try:
                            external, defaults, problems = parse_stop(feature)
                            for problem in problems:
                                ImportError.objects.create(
                                    run=run, external_id=str(index), message=problem
                                )
                            metrics["advertencias_servicios"] += len(problems)
                            if external in unique:
                                metrics["duplicados_fisicos"] += 1
                                merged = {
                                    tuple(s.items())
                                    for s in unique[external]["metadata"]["lineas"]
                                    + defaults["metadata"]["lineas"]
                                }
                                unique[external]["metadata"]["lineas"] = sorted(
                                    [dict(s) for s in merged],
                                    key=lambda s: (s["numero"], s["sentido"]),
                                )
                            else:
                                unique[external] = defaults
                        except ValueError as exc:
                            run.errors += 1
                            ImportError.objects.create(
                                run=run, external_id=str(index), message=str(exc)[:500]
                            )
                    metrics["paradas_oficiales_leidas"] = len(unique)
                    existing = {
                        p.external_id: p
                        for p in source.parada_set.filter(external_id__in=list(unique))
                    }
                    creates, updates = [], []
                    for external, defaults in unique.items():
                        old = existing.get(external)
                        if old is None:
                            creates.append(
                                Parada(source=source, external_id=external, **defaults)
                            )
                        elif any(getattr(old, k) != v for k, v in defaults.items()):
                            for key, value in defaults.items():
                                setattr(old, key, value)
                            old.updated_at = timezone.now()
                            updates.append(old)
                        else:
                            run.skipped += 1
                    Parada.objects.bulk_create(creates, batch_size=500)
                    if updates:
                        Parada.objects.bulk_update(
                            updates,
                            list(next(iter(unique.values()))) + ["updated_at"],
                            batch_size=500,
                        )
                    run.created, run.updated = len(creates), len(updates)
            if (match or rematch) and run.status != "UNCHANGED":
                match_routes(source, run, metrics)
                metrics["matching_done"] = True
            services = source.parada_set.filter(es_oficial=True).values_list(
                "metadata", flat=True
            )
            known = set(Linea.objects.values_list("numero", flat=True))
            metrics["lineas_reconocidas"] = len(
                {
                    s["numero"]
                    for metadata in services
                    for s in metadata.get("lineas", [])
                    if s["numero"] in known
                }
            )
            metrics["paradas_oficiales_totales"] = source.parada_set.filter(
                es_oficial=True
            ).count()
            metrics["ambiguedades_pendientes"] = StopMatchIssue.objects.filter(
                parada__source=source,
                status="pending",
                reason__in=["ambiguous_position", "ambiguous_branches"],
            ).count()
            metrics["dry_run"] = dry_run
            coverage(metrics)
            run.metrics = metrics
            run.status = (
                run.status
                if run.status == "UNCHANGED"
                else "PARTIAL" if run.errors else "SUCCESS"
            )
            run.finished_at = timezone.now()
            run.save()
            if dry_run:
                transaction.set_rollback(True)
            return run
    except Exception as exc:
        # Unexpected faults roll back ALL data, rather than committing a half-rematch.
        if dry_run:
            raise CommandError(
                f"Dry-run fallido, sin persistir cambios: {exc}"
            ) from exc
        source, _ = DataSource.objects.get_or_create(
            slug=source_slug, defaults={"nombre": "BA Data · Paradas oficiales"}
        )
        failed = ImportRun.objects.create(
            source=source,
            kind="paradas_oficiales",
            location=str(location)[:1000],
            status="FAILED",
            errors=1,
            finished_at=timezone.now(),
        )
        ImportError.objects.create(
            run=failed,
            message=f"Importación revertida: {type(exc).__name__}: {str(exc)[:400]}",
        )
        raise CommandError(f"Importación {failed.pk} revertida: {exc}") from exc
