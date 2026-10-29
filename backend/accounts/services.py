from transport.services import catalog, visited_by_line, line_progress
from gamification.services import total_points, level_for, rank_position


def profile_data(user, private=False):
    visited = visited_by_line(user)
    progresses = [
        line_progress(line, visited[line.pk])
        for line in catalog().filter(pk__in=visited)
    ]
    points = total_points(user)
    data = {
        "id": user.pk,
        "username": user.username,
        "nickname": user.nickname or user.username,
        "avatar": user.avatar,
        "puntos": points,
        "nivel": level_for(points),
        "paradas": sum(len(stops) for stops in visited.values()),
        "lineas_recorridas": len(visited),
        "ramales_completos": sum(
            b["completo"] for p in progresses for b in p["ramales"]
        ),
        "lineas_completas": sum(p["completo"] for p in progresses),
        "ranking_global": rank_position(user),
        "ranking_semanal": rank_position(user, "semanal"),
        "logros": list(
            user.logros.select_related("logro").values(
                "logro__slug", "logro__nombre", "logro__descripcion"
            )
        ),
        "lineas": progresses,
    }
    if private:
        data.update(
            email=user.email,
            public_profile=user.public_profile,
            theme=user.theme,
            ranking_amigos=rank_position(user, "amigos"),
        )
    return data
