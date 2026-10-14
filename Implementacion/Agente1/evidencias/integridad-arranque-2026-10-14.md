# Integridad de la versión al arrancar (#92, ADR 0010)

- **Estado:** implementado y verificado offline; el paso en el host queda para
  el operador designado y para la mesa final
- **Alcance:** manifest de versión (`manifest-version.json`), verificación
  fail-closed en modo operación (`--live`, el camino de las unidades
  `systemd/`) y su asiento en la auditoría
- **Relacionados:** ADR 0010, issue #92, `CONTEXT.md` (Cambio controlado,
  Versión del agente), `src/agente1/manifest_version.py`,
  `scripts/manifest_version.py`, `scripts/manifest_corte.py`

## 1. Qué se construyó

El manifest de versión fija el sha256 de **todo lo controlado que vive en el
repo**: `src/` (código, prompts, políticas, contratos), `migrations/`,
`uv.lock`, `pyproject.toml`, `scripts/` operativos y `systemd/`. La versión
sale de `pyproject.toml` (`[project].version`); el manifest viaja con ella en
la raíz del Agente 1 (`manifest-version.json`), **fuera** de las rutas que
recorre, así que no se controla a sí mismo.

Se genera con:

```bash
uv run python scripts/manifest_version.py --salida manifest-version.json
```

Es determinista: el mismo árbol produce el mismo archivo byte a byte, sin
timestamps volátiles y con orden estable. `scripts/manifest_corte.py` dejó de
mantener su lista `FUENTES` congelada en `gacetilla_v3`: ahora referencia
`version` y `manifest_version_sha256`, y sólo suma lo propio del corte
(configuración del adapter y referencia Git).

En **modo operación** —corridas con `--live`, que es como las unidades
`systemd/` invocan el scheduler— el agente compara el manifest con el árbol del
host antes de tocar la red. Si un archivo falta, sobra o no coincide, o si el
manifest está ausente o es inválido, **no arranca** (código de salida 2) y
deja el motivo en `logs/integridad-arranque.jsonl` con el archivo, el hash
esperado y el encontrado. Las corridas offline (`--tabla`), la CLI local y la
suite **no verifican**: el manifest se regenera al cortar una versión, no en
cada cambio.

## 2. Reproducción offline ejecutada (2026-10-14)

Copia del árbol controlado a un directorio aparte, gate corrido tres veces:
host intacto, prompt editado a mano y prompt restaurado. Salida real:

```
== 1. host intacto ==
resultado: PASS | version: 0.1.0
== 2. se edita un prompt en el host ==
no arranca: integridad_archivos_no_coinciden
  archivo: src/agente1/prompts/gacetilla_v6.txt | motivo: modificado
  hash_esperado:   be7ec6a7a1c52a38479f702da5aff7df0a1d85910ef902beb58e35854cdbf246
  hash_encontrado: a24a02fe3e405c9f9e82cfc4515096ddbbd987d5084af019987acef35d11e5f1
== 3. se restaura el prompt ==
resultado: PASS
== auditoria (logs/integridad-arranque.jsonl) ==
{"resultado": "PASS", "motivo": null, "version": "0.1.0", "archivos_esperados": 150, "discrepancias": []}
{"resultado": "FAIL", "motivo": "integridad_archivos_no_coinciden", "version": "0.1.0", "archivos_esperados": 150, "discrepancias": [{"archivo": "src/agente1/prompts/gacetilla_v6.txt", "hash_encontrado": "a24a02fe3e405c9f9e82cfc4515096ddbbd987d5084af019987acef35d11e5f1", "hash_esperado": "be7ec6a7a1c52a38479f702da5aff7df0a1d85910ef902beb58e35854cdbf246", "motivo": "modificado"}]}
{"resultado": "PASS", "motivo": null, "version": "0.1.0", "archivos_esperados": 150, "discrepancias": []}
```

El gate corrido sobre el tree versionado del commit de este issue da `PASS`
con 150 archivos controlados. Los tres casos (modificado, faltante y
sobrante) y los dos de manifest (ausente e inválido) están cubiertos por la
suite en `tests/test_manifest_version.py` (el fallo se acredita con el hash
esperado y el encontrado) y el cableado en `tests/test_integridad_arranque.py`
(`--live` no arranca; offline no exige manifest).

Marcas de alcance: esta reproducción es **offline y declarada** —no acredita
una corrida contra Workspace real ni el paso en el host—. No es un fake: usa
el mismo módulo, el mismo manifest y la misma auditoría que el modo operación.

## 3. Paso en vivo para el laboratorio y la mesa

Precondición: el host tiene el checkout de la versión y su
`manifest-version.json` (viaja con la versión; se regenera con el corte, no en
el host). El operador corre la corrida en modo operación como en el runbook del
scheduler (`--live` + `--confirm-write-workspace` + `--ollama-model`).

1. **Arranca.** Correr el disparo programado documentado. En la auditoría:

   ```bash
   tail -n 1 "$DIRECTORIO_SALIDA/logs/integridad-arranque.jsonl"
   # resultado=PASS, version=<la de la versión instalada>
   ```

2. **Se altera un prompt en el host** (el paso que la mesa muestra):

   ```bash
   printf '\n# edicion a mano\n' >> src/agente1/prompts/gacetilla_v6.txt
   ```

3. **No arranca.** Repetir el disparo: sale con código 2 y stdout
   `{"estado": "INVALIDA", "error": "integridad_archivos_no_coinciden"}`. La
   auditoría muestra el archivo y **los dos hashes**:

   ```bash
   tail -n 1 "$DIRECTORIO_SALIDA/logs/integridad-arranque.jsonl"
   # discrepancias[0]: archivo=src/agente1/prompts/gacetilla_v6.txt,
   # motivo=modificado, hash_esperado=<...>, hash_encontrado=<...>
   ```

4. **Se restaura.** `git -C <checkout> checkout -- src/agente1/prompts/gacetilla_v6.txt`
   (o restaurar desde el artefacto/versión). Repetir el disparo: vuelve
   `resultado=PASS` y la corrida sigue.

El paso 3 no envía, no publica y no deja borradores: el gate corre antes de
pedir credenciales y antes de cualquier llamada a Google.

## 4. Límites

- No acredita la corrida live contra Workspace: es la reproducción offline del
  mismo gate, más el procedimiento para el host.
- La **configuración por entorno** (IDs de planillas y Forms, scopes) queda
  fuera de este fail-closed por decisión del ADR 0010; su registro y aviso es
  del issue #94.
- El tag, el changelog y la versión del agente en la auditoría son del issue
  #93, dependiente de este.
