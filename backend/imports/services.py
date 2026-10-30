import hashlib
import csv
import io
import json
import math
from pathlib import Path
from urllib.parse import urlparse
import requests
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiLineString
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.utils import timezone
from transport.models import (
    Linea,
    Ramal,
    Recorrido,
    Parada,
    RecorridoParada,
    normalize_line,
)
from .models import DataSource, ImportRun, ImportError


def load_bytes(location):
    if urlparse(location).scheme in {"http", "https"}:
        with requests.get(
            location, timeout=(10, settings.IMPORT_TIMEOUT), stream=True
        ) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > settings.IMPORT_MAX_BYTES:
                    raise ValueError("La fuente supera el tamaño permitido.")
                chunks.append(chunk)
            raw = b"".join(chunks)
    else:
        path = Path(location)
        if path.stat().st_size > settings.IMPORT_MAX_BYTES:
            raise ValueError("El archivo supera el tamaño permitido.")
        raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def load_document(location):
    raw, checksum = load_bytes(location)
    return json.loads(raw), checksum


def load_csv_document(location):
    raw, checksum = load_bytes(location)
    try:
        reader = csv.DictReader(
            io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True
        )
        fields = reader.fieldnames or []
        required = {"linea", "recorrido", "sentido", "l_r_s"}
        if len(fields) != len(set(fields)) or not required.issubset(fields):
            raise ValueError(
                "El CSV requiere columnas únicas: linea, recorrido, sentido y l_r_s."
            )
        features = [{"type": "Feature", "properties": row} for row in reader]
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError(
            "El CSV debe ser UTF-8 y tener filas y comillas válidas."
        ) from exc
    return {"type": "FeatureCollection", "features": features}, checksum


def validate_geojson(document):
    if (
        not isinstance(document, dict)
        or document.get("type") != "FeatureCollection"
        or not isinstance(document.get("features"), list)
    ):
        raise ValueError("Se esperaba un GeoJSON FeatureCollection.")
    crs = document.get("crs", {}).get("properties", {}).get("name", "")
    if crs and not any(x in crs.upper() for x in ["CRS84", "4326"]):
        raise ValueError("La fuente debe estar en WGS84 / SRID 4326.")
    if not document["features"]:
        raise ValueError("La fuente está vacía. Se conservó el catálogo.")


def geometry(data, expected):
    if not isinstance(data, dict):
        raise ValueError("Falta una geometría válida.")
    geom = GEOSGeometry(json.dumps(data), srid=4326)
    if geom.empty or not geom.valid:
        raise ValueError("Geometría vacía o inválida.")
    if expected == "MultiLineString" and geom.geom_type == "LineString":
        geom = MultiLineString(geom, srid=4326)
    if geom.geom_type != expected or geom.hasz:
        raise ValueError(f"Se esperaba geometría {expected} 2D.")
    xmin, ymin, xmax, ymax = geom.extent
    if not all(math.isfinite(v) for v in geom.extent) or not (
        -180 <= xmin <= xmax <= 180 and -90 <= ymin <= ymax <= 90
    ):
        raise ValueError("Coordenadas fuera de WGS84.")
    return geom


ROUTE_METADATA = [
    "fid",
    "linea",
    "recorrido",
    "sentido",
    "l_r_s",
    "modalidad",
    "jurisdicci",
    "camara",
    "desde",
    "hasta",
]


def route_properties(feature, csv_catalogue=False):
    props = feature.get("properties")
    if not isinstance(props, dict):
        raise ValueError("Faltan properties.")
    if csv_catalogue and (
        None in props or any(value is None for value in props.values())
    ):
        raise ValueError("La fila CSV no tiene la cantidad de columnas esperada.")
    number = normalize_line(props.get("linea", ""))
    branch_name = str(props.get("recorrido") or "").strip()
    direction = str(props.get("sentido") or "").strip().upper()
    external = str(props.get("l_r_s") or "").strip()
    if (
        not branch_name
        or len(branch_name) > 100
        or direction not in {"IDA", "VUELTA"}
        or not external
        or len(external) > 100
    ):
        raise ValueError("recorrido, sentido o l_r_s inválido.")
    if csv_catalogue and external != f"{int(number):03d}{branch_name}{direction}":
        raise ValueError("l_r_s no coincide con la línea, el ramal y el sentido.")
    return props, number, branch_name, direction, external


def route_target(props, number, branch_name, direction, external, source):
    line, _ = Linea.objects.get_or_create(
        numero=number, defaults={"source": source, "external_id": str(props["linea"])}
    )
    if (
        source.slug == "badata"
        and line.source_id
        and line.source.slug == "badata-muestra"
    ):
        line.source = source
        line.external_id = str(props["linea"])
        line.save(update_fields=["source", "external_id", "updated_at"])
    branch, _ = Ramal.objects.get_or_create(linea=line, nombre=branch_name)
    route = (
        Recorrido.objects.select_related("source")
        .filter(source=source, external_id=external)
        .first()
    )
    if route is None:
        route = (
            Recorrido.objects.select_related("source")
            .filter(ramal=branch, sentido=direction)
            .first()
        )
        if route and not (
            source.slug == "badata"
            and route.source.slug == "badata-muestra"
            and route.external_id == external
        ):
            raise ValueError(
                "El recorrido pertenece a otra fuente o tiene otro identificador. Requiere revisión."
            )
    if route and (route.ramal_id != branch.pk or route.sentido != direction):
        raise ValueError(
            "Cambió la identidad de un recorrido; requiere revisión administrativa."
        )
    return branch, route


def import_catalogue_route(feature, source):
    props, number, name, direction, external = route_properties(
        feature, csv_catalogue=True
    )
    branch, route = route_target(props, number, name, direction, external, source)
    metadata = {key: props.get(key, "") for key in ROUTE_METADATA}
    checksum = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    if (
        route
        and route.source_id == source.pk
        and route.catalogue_format == "csv"
        and route.checksum == checksum
    ):
        return "skipped"
    created = route is None
    if created:
        route = Recorrido(ramal=branch, sentido=direction, external_id=external)
    route.source = source
    route.metadata = metadata
    route.checksum = checksum
    route.catalogue_format = "csv"
    # Importar metadata no reemplaza trazados ni ocurrencias históricas.
    route.save()
    return "created" if created else "updated"


def import_route(feature, source):
    props, number, name, direction, external = route_properties(feature)
    geom = geometry(feature.get("geometry"), "MultiLineString")
    branch, route = route_target(props, number, name, direction, external, source)
    created = route is None
    if created:
        route = Recorrido(
            ramal=branch, sentido=direction, external_id=external, source=source
        )
    changed = (
        created
        or route.source_id != source.pk
        or route.geometria != geom
        or route.geometria_source_id != source.pk
    )
    if route.catalogue_format != "csv":
        checksum = hashlib.sha256(
            json.dumps(feature, sort_keys=True).encode()
        ).hexdigest()
        changed = changed or route.checksum != checksum
        route.metadata = {key: props.get(key) for key in ROUTE_METADATA}
        route.checksum = checksum
    if not changed:
        return "skipped"
    route.source = source
    route.geometria = geom
    route.geometria_source = source
    route.save()
    return "created" if created else "updated"


def import_stop(feature, source):
    props = feature.get("properties")
    if not isinstance(props, dict):
        raise ValueError("Faltan properties.")
    external = str(props.get("id", props.get("external_id", ""))).strip()
    if not external or len(external) > 100:
        raise ValueError("La parada necesita un id físico estable.")
    geom = geometry(feature.get("geometry"), "Point")
    relations = props.get("recorridos")
    if relations is None and props.get("l_r_s") and "orden" in props:
        relations = [{"l_r_s": props["l_r_s"], "orden": props["orden"]}]
    if not isinstance(relations, list) or not relations:
        raise ValueError(
            "Sin relación explícita l_r_s + orden. No se infiere por proximidad."
        )
    validated = []
    for relation in relations:
        if not isinstance(relation, dict):
            raise ValueError("Relación inválida.")
        external_route = str(relation.get("l_r_s", ""))
        routes = Recorrido.objects.filter(external_id=external_route)
        route_source = relation.get("source")
        if route_source:
            routes = routes.filter(source__slug=route_source)
        if routes.count() != 1:
            raise ValueError(
                "Recorrido inexistente o ambiguo. Indicá source si es necesario."
            )
        order = relation.get("orden")
        if isinstance(order, bool) or not isinstance(order, int) or order < 0:
            raise ValueError("orden debe ser entero no negativo.")
        validated.append((routes.get(), order))
    defaults = {
        "ubicacion": geom,
        **{
            field: str(props.get(field) or "")[:limit]
            for field, limit in [
                ("nombre", 250),
                ("direccion", 250),
                ("esquina", 200),
                ("barrio", 100),
                ("comuna", 30),
            ]
        },
    }
    previous = Parada.objects.filter(source=source, external_id=external).first()
    changed = not previous or any(
        getattr(previous, k) != v for k, v in defaults.items()
    )
    stop, created = (
        Parada.objects.update_or_create(
            source=source, external_id=external, defaults=defaults
        )
        if changed
        else (previous, False)
    )
    for route, order in validated:
        occurrence = RecorridoParada.objects.filter(
            recorrido=route, orden=order
        ).first()
        if occurrence and occurrence.parada_id != stop.pk:
            # Los viajes referencian ocurrencias: nunca reasignarlas silenciosamente.
            raise ValueError(
                "El orden está ocupado por otra parada. Requiere revisión antes de reemplazarlo."
            )
        _, added = RecorridoParada.objects.get_or_create(
            recorrido=route, orden=order, defaults={"parada": stop}
        )
        changed = changed or added
    return "created" if created else "updated" if changed else "skipped"


def run_import(
    location, kind, handler, source_slug="badata", force=False, loader=load_document
):
    source, _ = DataSource.objects.get_or_create(
        slug=source_slug,
        defaults={
            "nombre": "Buenos Aires Data" if source_slug == "badata" else source_slug
        },
    )
    run = ImportRun.objects.create(source=source, kind=kind)
    lock_kind = "recorridos" if kind in {"catalogo_csv", "recorridos"} else kind
    lock = int.from_bytes(
        hashlib.sha256(f"{source_slug}:{lock_kind}".encode()).digest()[:8], signed=True
    )
    locked = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock])
            locked = cursor.fetchone()[0]
        if not locked:
            raise ValueError("Ya hay una importación de esta fuente en ejecución.")
        document, checksum = loader(location)
        run.checksum = checksum
        validate_geojson(document)
        previous = (
            ImportRun.objects.filter(
                source=source, kind=kind, status__in=["SUCCESS", "PARTIAL"]
            )
            .exclude(pk=run.pk)
            .order_by("-pk")
            .first()
        )
        if (
            not force
            and previous
            and previous.status == "SUCCESS"
            and previous.checksum == checksum
        ):
            run.status = "UNCHANGED"
            run.skipped = len(document["features"])
            return run
        for index, feature in enumerate(document["features"]):
            try:
                if not isinstance(feature, dict) or feature.get("type") != "Feature":
                    raise ValueError("Elemento inválido; se esperaba Feature.")
                with transaction.atomic():
                    # Same catalogue lock as official matching and trip recording.
                    # Take it before any entity/user row lock to avoid deadlocks.
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [6132041])
                    outcome = handler(feature, source)
                setattr(run, outcome, getattr(run, outcome) + 1)
            except Exception as exc:
                run.errors += 1
                message = (
                    str(exc)[:500]
                    if isinstance(exc, ValueError)
                    else f"Registro inválido ({type(exc).__name__}); revisar estructura o constraints."
                )
                ImportError.objects.create(
                    run=run, external_id=str(index), message=message
                )
        run.status = "PARTIAL" if run.errors else "SUCCESS"
    except Exception as exc:
        run.status = "FAILED"
        run.errors += 1
        message = (
            str(exc)[:500]
            if isinstance(exc, ValueError)
            else f"No se pudo leer la fuente ({type(exc).__name__})."
        )
        ImportError.objects.create(run=run, message=message)
        raise CommandError(f"Importación {run.pk} fallida: {message}") from exc
    finally:
        run.finished_at = timezone.now()
        run.save()
        if locked:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [lock])
    return run
