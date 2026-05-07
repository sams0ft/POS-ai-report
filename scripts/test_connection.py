"""Prueba de conexión a Supabase — ejecutar desde la raíz del proyecto."""

import asyncio
import sys

import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()


async def test_connection(label: str, url: str) -> bool:
    """Intenta conectar a PostgreSQL y ejecuta una query básica."""
    # asyncpg no acepta el prefijo SQLAlchemy — lo removemos
    raw_url = url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"\n[{label}]")
    print(f"  Host: {_extract_host(raw_url)}")

    try:
        conn = await asyncpg.connect(raw_url, ssl="require")
        version = await conn.fetchval("SELECT version();")
        await conn.close()
        print(f"  Estado: OK")
        print(f"  Version: {version.split(',')[0]}")
        return True
    except Exception as e:
        print(f"  Estado: ERROR")
        print(f"  Detalle: {e}")
        return False


def _extract_host(url: str) -> str:
    """Extrae el host de una URL de conexion."""
    try:
        return url.split("@")[1].split(":")[0]
    except IndexError:
        return "desconocido"


async def main() -> None:
    pos_url = os.getenv("POS_DATABASE_URL", "")
    analytics_url = os.getenv("ANALYTICS_DATABASE_URL", "")

    if not pos_url:
        print("ERROR: POS_DATABASE_URL no está configurado en .env")
        sys.exit(1)

    resultados = []
    resultados.append(await test_connection("POS (read-only)", pos_url))

    if analytics_url and analytics_url != pos_url:
        resultados.append(await test_connection("Analítica (read-write)", analytics_url))
    else:
        print("\n[Analítica] Misma conexión que POS — omitida")

    print()
    if all(resultados):
        print("Todas las conexiones exitosas.")
        sys.exit(0)
    else:
        print("Una o más conexiones fallaron.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
