"""Enrich the CSV catalogue with official geometry; never create catalogue rows."""

import hashlib
import json
import re
import time
from collections import defaultdict

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.utils import timezone

from transport.models import Recorrido, normalize_line
from .models import DataSource, ImportRun, ImportError
from .services import geometry, load_document, validate_geojson


def normalized_branch(value):
    return " ".join(str(value).split()).upper()


def normalized_external(value, number=None):
    text = normalized_branch(value)
    prefix = (
        rf"0*{re.escape(number)}" if number and number.isdigit()
        else re.escape(number) if number else None
    )
    match = (
        re.fullmatch(rf"{prefix}\s*(.*?)\s*(IDA|VUELTA)", text)
        if prefix
        else None
    )
    if not match:
        return text
    branch, direction = match.groups()
    return f"{normalize_line(number)}|{normalized_branch(branch)}|{direction}"


def route_identity(route):
    return (
        route.ramal.linea.numero,
        normalized_branch(route.ramal.nombre),
        route.sentido,
    )


def properties(feature):
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise ValueError("Se esperaba Feature.")
    raw = feature.get("properties")
    if not isinstance(raw, dict) or not raw or len(json.dumps(raw)) > 20000:
        raise ValueError("Faltan properties válidas o exceden el tamaño máximo.")
    props = {str(key).strip().lower(): value for key, value in raw.items()}
    values = {}
    for key, limit in [
        ("linea", 10),
        ("recorrido", 100),
        ("sentido", 10),
        ("l_r_s", 100),
    ]:
        value = props.get(key, "")
        if isinstance(value, (dict, list, bool)) or value is None:
            raise ValueError(f"{key}: tipo inválido.")
        value = " ".join(str(value).split())
        if len(value) > limit:
            raise ValueError(f"{key}: longitud excesiva.")
        values[key] = value
    if not values["linea"]:
        raise ValueError("Falta el identificador de línea.")
    try:
        number = normalize_line(values["linea"])
    except ValueError:
        number = normalized_branch(values["linea"])
    branch = normalized_branch(values["recorrido"])
    direction = {"I": "IDA", "V": "VUELTA", "IDA": "IDA", "VUELTA": "VUELTA"}.get(
        values["sentido"].upper()
    )
    if not branch or direction is None:
        raise ValueError("Ramal o sentido inválidos.")
    return (number, branch, direction), values["l_r_s"]


def log_issue(run, index, external, reason, candidates=None):
    ImportError.objects.create(
        run=run,
        external_id=str(external or index)[:150],
        message=json.dumps(
            {"feature": index, "motivo": reason, "candidatos": candidates or []},
            ensure_ascii=False,
        )[:500],
    )


def run_geometry_import(
    location, source_slug="badata", force=False, dry_run=False, only_missing=False
):
    kind = "geometrias_muestra" if only_missing else "geometrias"
    start = time.monotonic()
    metrics = {
        name: 0
        for name in [
            "features_geojson",
            "match_exacto",
            "match_secundario",
            "sin_match",
            "conflictos",
            "geometrias_nuevas",
            "geometrias_actualizadas",
            "sin_cambios",
            "duplicados_identicos",
            "errores",
        ]
    }
    try:
        with transaction.atomic():
            # Same lock as rematching and shared trip registration, before row locks.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [6132041])
            source, _ = DataSource.objects.get_or_create(
                slug=source_slug,
                defaults={
                    "nombre": "BA Data · Geometrías de recorridos",
                    "url": settings.BA_DATA_RECORRIDOS_GEOJSON_URL,
                },
            )
            run = ImportRun.objects.create(
                source=source, kind=kind, location=str(location)[:1000]
            )
            document, run.checksum = load_document(location)
            validate_geojson(document)
            metrics["features_geojson"] = len(document["features"])
            routes = list(
                Recorrido.objects.select_for_update()
                .select_related("ramal__linea")
                .filter(catalogue_format="csv")
                .order_by("pk")
            )
            metrics["recorridos_catalogo_total"] = len(routes)
            exact, raw_exact, logical = (
                defaultdict(list),
                defaultdict(list),
                defaultdict(list),
            )
            catalogue_signature = []
            for route in routes:
                exact[
                    normalized_external(route.external_id, route.ramal.linea.numero)
                ].append(route)
                raw_exact[normalized_branch(route.external_id)].append(route)
                logical[route_identity(route)].append(route)
                catalogue_signature.append(
                    (route.pk, route.external_id, route_identity(route))
                )
            signature = hashlib.sha256(
                json.dumps(catalogue_signature, sort_keys=True).encode()
            ).hexdigest()
            metrics["catalogue_signature"] = signature
            previous = (
                source.runs.filter(kind=kind, status__in=["SUCCESS", "PARTIAL"])
                .exclude(pk=run.pk)
                .order_by("-pk")
                .first()
            )
            if (
                not force
                and previous
                and previous.status == "SUCCESS"
                and previous.checksum == run.checksum
                and previous.metrics.get("catalogue_signature") == signature
            ):
                run.status = "UNCHANGED"
                run.skipped = metrics["features_geojson"]
                metrics["sin_cambios"] = (
                    previous.created
                    + previous.updated
                    + previous.metrics.get("sin_cambios", 0)
                )
                metrics["omitidos_checksum"] = run.skipped
                metrics["match_exacto"] = previous.metrics.get("match_exacto", 0)
                metrics["match_secundario"] = previous.metrics.get(
                    "match_secundario", 0
                )
                metrics["sin_match"] = previous.metrics.get("sin_match", 0)
                metrics["reprocesado"] = False
            else:
                staged = defaultdict(list)
                for index, feature in enumerate(document["features"]):
                    external = ""
                    try:
                        identity, external = properties(feature)
                        try:
                            geom = geometry(feature.get("geometry"), "MultiLineString")
                        except Exception as exc:
                            raise ValueError(
                                "Geometría LineString/MultiLineString inválida."
                            ) from exc
                        normalized_id = (
                            normalized_external(external, identity[0])
                            if external
                            else ""
                        )
                        candidates = (
                            raw_exact.get(normalized_branch(external), [])
                            if external
                            else []
                        )
                        if (
                            not candidates
                            and "|" in normalized_id
                            and tuple(normalized_id.split("|")) != identity
                        ):
                            metrics["conflictos"] += 1
                            log_issue(
                                run,
                                index,
                                external,
                                "l_r_s contradice línea, ramal o sentido declarados",
                            )
                            continue
                        candidates = candidates or (
                            exact.get(normalized_id, []) if external else []
                        )
                        if len(candidates) > 1 or (
                            candidates and route_identity(candidates[0]) != identity
                        ):
                            metrics["conflictos"] += 1
                            log_issue(
                                run,
                                index,
                                external,
                                "Identificador y atributos contradicen el catálogo",
                                [r.pk for r in candidates],
                            )
                            continue
                        if candidates:
                            route, method = candidates[0], "match_exacto"
                        else:
                            candidates = logical.get(identity, [])
                            if len(candidates) != 1:
                                metrics["sin_match"] += 1
                                close = [
                                    r.pk
                                    for r in routes
                                    if r.ramal.linea.numero == identity[0]
                                    and r.sentido == identity[2]
                                ]
                                log_issue(
                                    run,
                                    index,
                                    external,
                                    "Sin correspondencia única en el catálogo CSV",
                                    close[:30],
                                )
                                continue
                            route, method = candidates[0], "match_secundario"
                        metrics[method] += 1
                        staged[route.pk].append((index, external, route, geom))
                    except ValueError as exc:
                        run.errors += 1
                        log_issue(run, index, external, str(exc))
                changes = []
                for items in staged.values():
                    if len({bytes(item[3].wkb) for item in items}) > 1:
                        metrics["conflictos"] += len(items)
                        for index, external, route, geom in items:
                            log_issue(
                                run,
                                index,
                                external,
                                "Features contradictorias para el mismo recorrido",
                                [route.pk],
                            )
                        continue
                    index, external, route, geom = items[0]
                    metrics["duplicados_identicos"] += len(items) - 1
                    if route.geometria == geom or (
                        only_missing and route.geometria is not None
                    ):
                        run.skipped += len(items)
                        metrics["sin_cambios"] += 1
                        continue
                    previous_hash = (
                        hashlib.sha256(bytes(route.geometria.wkb)).hexdigest()
                        if route.geometria
                        else None
                    )
                    created = route.geometria is None
                    route.geometria = geom
                    route.geometria_source = source
                    route.requiere_rematch = True
                    route.save(
                        update_fields=[
                            "geometria",
                            "geometria_source",
                            "requiere_rematch",
                            "updated_at",
                        ]
                    )
                    run.created += int(created)
                    run.updated += int(not created)
                    run.skipped += len(items) - 1
                    metrics[
                        "geometrias_nuevas" if created else "geometrias_actualizadas"
                    ] += 1
                    changes.append(
                        {
                            "recorrido": route.pk,
                            "external_id": route.external_id,
                            "anterior_sha256": previous_hash,
                            "nuevo_sha256": hashlib.sha256(bytes(geom.wkb)).hexdigest(),
                        }
                    )
                metrics["cambios"] = changes
                metrics["reprocesado"] = True
                run.status = (
                    "PARTIAL" if run.errors or metrics["conflictos"] else "SUCCESS"
                )
            metrics["errores"] = run.errors
            metrics["recorridos_con_geometria_total"] = sum(
                r.geometria is not None for r in routes
            )
            total = metrics["recorridos_catalogo_total"]
            metrics["cobertura_geometria_pct"] = (
                round(100 * metrics["recorridos_con_geometria_total"] / total, 2)
                if total
                else 0
            )
            metrics["duracion_segundos"] = round(time.monotonic() - start, 3)
            metrics["dry_run"] = dry_run
            metrics["solo_faltantes"] = only_missing
            run.metrics = metrics
            run.finished_at = timezone.now()
            run.save()
            if dry_run:
                transaction.set_rollback(True)
            return run
    except Exception as exc:
        if not dry_run:
            source, _ = DataSource.objects.get_or_create(
                slug=source_slug,
                defaults={"nombre": "BA Data · Geometrías de recorridos"},
            )
            failed = ImportRun.objects.create(
                source=source,
                kind=kind,
                location=str(location)[:1000],
                status="FAILED",
                errors=1,
                finished_at=timezone.now(),
            )
            ImportError.objects.create(
                run=failed,
                message=f"Importación revertida ({type(exc).__name__}): {str(exc)[:400]}",
            )
        raise CommandError(f"Importación de geometrías revertida: {exc}") from exc
