import json
import platform
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from aiohttp import web

from database import MOD_DB_PATH
from role_shop import ROLE_DB_PATH


_runner = None
_site = None


def _command_count(commands) -> int:
    total = 0

    for command in commands:
        children = getattr(command, "commands", None)
        if children:
            total += _command_count(children)
        else:
            total += 1

    return total


def _command_list(commands) -> list[dict]:
    result = []

    for command in commands:
        children = getattr(command, "commands", None)
        item = {
            "name": getattr(command, "name", None),
            "qualified_name": getattr(command, "qualified_name", None),
            "description": getattr(command, "description", None),
            "type": command.__class__.__name__,
        }

        if children:
            item["children"] = _command_list(children)

        result.append(item)

    return result


def _safe_iso(value) -> str | None:
    return value.isoformat() if value else None


def _quote_identifier(name: str) -> str:
    return f'"{name.replace(chr(34), chr(34) + chr(34))}"'


def _dump_sqlite_database(db_path: str) -> dict:
    path = Path(db_path)

    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "tables": {},
        }

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    table_names = [row["name"] for row in cursor.fetchall()]

    tables = {}
    for table_name in table_names:
        quoted_name = _quote_identifier(table_name)
        cursor.execute(f"SELECT * FROM {quoted_name}")
        rows = [dict(row) for row in cursor.fetchall()]
        tables[table_name] = {
            "row_count": len(rows),
            "rows": rows,
        }

    cursor.close()
    conn.close()

    return {
        "path": str(path),
        "exists": True,
        "tables": tables,
    }


def _request_info(request: web.Request, generated_at: datetime) -> dict:
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else request.remote
    local_time = generated_at.astimezone()

    return {
        "ip": ip,
        "remote": request.remote,
        "method": request.method,
        "path": request.path,
        "query": dict(request.query),
        "user_agent": request.headers.get("User-Agent"),
        "referer": request.headers.get("Referer"),
        "host": request.headers.get("Host"),
        "requested_at": generated_at.isoformat(),
        "date_utc": generated_at.strftime("%Y-%m-%d"),
        "time_utc": generated_at.strftime("%H:%M:%S"),
        "requested_at_local": local_time.isoformat(),
        "date_local": local_time.strftime("%Y-%m-%d"),
        "time_local": local_time.strftime("%H:%M:%S"),
        "timezone": local_time.tzname(),
        "headers": {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in {"authorization", "cookie"}
        },
    }


def _request_port(request: web.Request) -> int | None:
    host = request.headers.get("Host", "")

    if ":" not in host:
        return None

    port = host.rsplit(":", 1)[1]
    return int(port) if port.isdigit() else None


def _with_cors(response: web.StreamResponse) -> web.StreamResponse:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _bot_stats(bot, db) -> dict:
    guilds = list(bot.guilds)
    member_count = sum(guild.member_count or 0 for guild in guilds)

    return {
        "bot_name": str(bot.user) if bot.user else "UltimaOka",
        "registered_users": db.count_users(),
        "event_subscribers": db.count_event_ping_users(),
        "members": member_count,
        "servers": len(guilds),
        "commands": _command_count(bot.tree.get_commands()),
        "latency_ms": round(bot.latency * 1000),
        "status": "online" if bot.is_ready() else "starting",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def setup_dashboard_api(bot, db, host: str = "127.0.0.1", port: int = 8080) -> None:
    global _runner, _site

    if _runner is not None:
        return

    dashboard_dir = Path(__file__).resolve().parent / "DashBoard" / "html"

    async def stats_handler(_request):
        return _with_cors(web.json_response(_bot_stats(bot, db)))

    async def devraw_handler(request):
        generated_at = datetime.now(timezone.utc)
        guilds = list(bot.guilds)
        payload = {
            "request": _request_info(request, generated_at),
            "dashboard": {
                "generated_at": generated_at.isoformat(),
                "host": host,
                "port": _request_port(request),
            },
            "bot": {
                "stats": _bot_stats(bot, db),
                "user": {
                    "id": bot.user.id if bot.user else None,
                    "name": getattr(bot.user, "name", None) if bot.user else None,
                    "display_name": getattr(bot.user, "display_name", None) if bot.user else None,
                    "global_name": getattr(bot.user, "global_name", None) if bot.user else None,
                },
                "latency": bot.latency,
                "latency_ms": round(bot.latency * 1000),
                "is_ready": bot.is_ready(),
                "guilds": [
                    {
                        "id": guild.id,
                        "name": guild.name,
                        "owner_id": guild.owner_id,
                        "member_count": guild.member_count,
                        "created_at": _safe_iso(guild.created_at),
                        "description": guild.description,
                        "premium_tier": guild.premium_tier,
                        "premium_subscription_count": guild.premium_subscription_count,
                        "roles_count": len(guild.roles),
                        "channels_count": len(guild.channels),
                        "text_channels_count": len(guild.text_channels),
                        "voice_channels_count": len(guild.voice_channels),
                        "categories_count": len(guild.categories),
                        "emojis_count": len(guild.emojis),
                        "stickers_count": len(guild.stickers),
                        "features": list(guild.features),
                    }
                    for guild in guilds
                ],
                "commands": _command_list(bot.tree.get_commands()),
            },
            "databases": {
                "users": _dump_sqlite_database(db.db_path),
                "moderation": _dump_sqlite_database(MOD_DB_PATH),
                "role_shop": _dump_sqlite_database(ROLE_DB_PATH),
            },
            "runtime": {
                "python": sys.version,
                "platform": platform.platform(),
            },
        }
        body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        filename = f"devraw-{generated_at.strftime('%Y%m%d-%H%M%S')}.json"
        response = web.Response(
            text=body,
            content_type="application/json",
            charset="utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

        return _with_cors(response)

    async def options_handler(_request):
        return _with_cors(web.Response(status=204))

    async def index_handler(_request):
        return web.FileResponse(dashboard_dir / "main.html")

    for current_port in range(port, port + 10):
        app = web.Application()
        app.router.add_get("/api/stats", stats_handler)
        app.router.add_get("/api/devraw", devraw_handler)
        app.router.add_options("/api/stats", options_handler)
        app.router.add_options("/api/devraw", options_handler)
        app.router.add_get("/", index_handler)
        app.router.add_get("/main.html", index_handler)
        app.router.add_static("/", dashboard_dir)

        runner = web.AppRunner(app)
        await runner.setup()

        try:
            site = web.TCPSite(runner, host, current_port)
            await site.start()
        except OSError:
            await runner.cleanup()
            continue

        _runner = runner
        _site = site
        print(f"Dashboard: http://{host}:{current_port}")
        return

    print(f"Dashboard error: ports {port}-{port + 9} are busy")
