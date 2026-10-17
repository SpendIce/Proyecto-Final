# Recorrido — post de efeméride HU-011 desde Historia Viva (#85)

**Estado institucional:** PENDIENTE
**Estado técnico:** pipeline offline provisional, `PROVISIONAL_NO_INSTITUCIONAL`.
**Contratos:** `post_creative_efemeride_v1` (provisional), prompts
`post_*_efemeride_v1` (provisionales) y `historia_viva_consulta_candidate_v1`
(`CANDIDATO_NO_INSTITUCIONAL`, posición unilateral de A1 pendiente de acuerdo
en el issue #17).

## Qué demuestra

- Que A1 consulta a Historia Viva **por el puerto, nunca por un adapter
  propio**: `procesar_post_efemeride` recibe cualquier implementación de
  `HistoriaViva`. La misma corrida pasa por `HistoriaVivaFake` en memoria y
  por `ClienteHistoriaViva` con `TransporteHistoriaVivaFake`, porque el
  cliente implementa el mismo puerto y valida las respuestas crudas antes de
  producir los objetos del dominio.
- Que la efeméride se compone del lado de A1 con
  `componer_material_efemeride`: una búsqueda por período, no un pedido de
  efeméride a A2. Historia Viva devuelve fragmentos citables, no prosa, y el
  modelo tampoco escribe hechos: redacta `gancho`, `prosa`, `cta` y hashtags
  del contrato `post_creative_efemeride_v1` mientras el renderer intercala
  literalmente el fragmento elegido con su cita.
- Que **la cita conserva la identidad completa de la fuente**: cada
  fragmento se renderiza con `pieza_id / fragmento_id (, ubicacion)
  (expresión temporal)`. La expresión sale de
  `RangoHistorico.expresion_temporal`: una pieza con precisión `mes` se cita
  como «agosto de 1926», nunca como día exacto, aunque el rango traiga días.
- Que **el post cita una sola referencia, elegida por fecha y por extensión**.
  De los fragmentos que devuelve el puerto se descartan los que no sustentan
  la fecha consultada (la fecha de la fuente tiene que caer dentro del
  período, el solapamiento no alcanza y la precisión de mes, año o década no
  se trata como un día exacto). Entre los elegibles se conserva el orden de
  Historia Viva y se publica el primero que entra completo en el canal,
  presupuestando el texto citado, la cita, la expresión temporal, la
  estructura y el espacio que ocupan la creatividad y los hashtags; si no
  entra, se prueba el siguiente. Las referencias no utilizadas y su motivo
  quedan en el borrador, fuera del texto publicable y de su cómputo de
  extensión. Sin elegibles, la causa es temporal (`material_insuficiente`);
  sin ninguno que entre, la causa es de extensión (`material_no_utilizable`),
  distinta de una falla de generación. La consulta no se reduce a un
  fragmento: se pide el límite completo para poder descartar al primero.
- Que la salida del modelo pasa **los mismos gates de HU-011** —mismo parser
  de `posts.py`, mismos códigos, mismo reintento acotado con feedback— y que
  `hechos_extra` declara además los textos citados, las citas, la expresión
  temporal y el mes de la efeméride: si la zona creativa repite alguno, cae
  con `source_fact_in_creative_field`. Un fragmento que narra un acto
  institucional («el Consejo aprobó…») sí se cita, porque es afirmación
  atribuida a la fuente y no estado del borrador; el gate de acciones sigue
  pleno sobre lo que escribe el modelo.
- Que **sin material no hay post**: una consulta vacía termina `INCOMPLETA` /
  `material_insuficiente` sin invocar al generador ni escribir borrador. No
  hay un hueco que el modelo pueda rellenar con una afirmación inventada.
- Que la procedencia es **declarada, no inferida**: `procedencia` es del
  vocabulario `insumo_a2` / `synthetic_test`; viaja a la auditoría como
  `data_origin` y al borrador como línea `_Procedencia: …_`, visible para
  quien valida y ajena al texto del post. En el log se registran la versión
  del contrato de consulta, el conteo de fragmentos, los `pieza_id` de las
  fuentes y el tema como hash: nunca el contenido de los fragmentos ni
  texto remoto sin sanitizar.
- Que el borrador es `efemeride-<período>-<hash>-<canal>` —id derivado del
  pedido, estable y dentro de la allowlist de objetos— y que queda
  `PENDIENTE_VALIDACION` con `BORRADOR — NO PUBLICAR`: se declara
  `publicacion` pendiente en el registro de decisiones (#72) y los links
  `publique`/`descarte` los firma una persona del padrón. Nada publica.

## Qué NO demuestra

- **No hay transporte productivo.** El adapter HTTP de Historia Viva queda
  diferido al acuerdo del issue #17 —bloqueado por #12—: ninguna prueba tocó
  la red y el fake nunca suplanta una instancia real. La corrida live exige
  además el contrato acordado (OpenAPI canónico, tag fijado, enums), la
  identidad por token y una instancia disponible de A2.
- **El contrato no está acordado.** `historia_viva_cliente_candidate_v1` es
  la posición de A1: los enums de `tipo`, la deduplicación por
  `Idempotency-Key` y la forma cerrada de las respuestas son propuestas sin
  confirmación de A2.
- **No es calidad de Ollama ni de redacción.** El recorrido usa
  `FakeGenerator` con una salida de muestra: verifica conformidad
  contractual, citas y gates, no grounding semántico ni tono. La medición
  live del modelo para esta pieza queda para el corte correspondiente.
- **No acredita validación SEU ni TRL 3.** La política de redes, la
  allowlist de hashtags y el criterio editorial siguen provisionales; la
  decisión de publicación sigue siendo humana.
- **El disparo no está cableado al canal.** `intenciones_v3` no tiene una
  intención de efeméride —resolver una fecha desde prosa del pedido es un
  cambio de contrato aparte— y el pipeline se invoca programáticamente
  (script o CLI), no por scheduler ni por el canal de pedidos.
- **El aporte de vuelta a A2 no se ejercita.** `registrar_aporte` existe en
  el puerto pero el issue define el flujo consulta → borrador; devolver el
  post validado al acervo es trabajo posterior.

## Antes de empezar

- Una terminal en `Implementacion/Agente1`. Sin red ni credenciales.
- Los fragmentos del recorrido viven en
  `data/fragmentos_historia_viva_sinteticos.json` y son **sintéticos**: dos
  piezas de mentira (`pie-sint-acta-001`, `pie-sint-gacetilla-002`) con tres
  fragmentos, uno con precisión `mes` para mostrar que la cita no afirma día
  exacto. Tienen la forma del contrato candidato y se cargan en
  `HistoriaVivaFake`; por eso la corrida declara `synthetic_test`.

## Paso a paso (offline)

```bash
uv run python scripts/post_efemeride_demo.py \
  --directorio salida/post-efemeride-demo
```

El script emite un JSON por fase —`generacion`, `decision`, `sin_material`—
con estados, ids y enlaces, nunca el texto del post ni los fragmentos en
stdout. Exit `0` cuando el borrador quedó `PENDIENTE_VALIDACION` y el caso
vacío `INCOMPLETA`.

Qué verificar después:

1. `salida/post-efemeride-demo/borradores/efemeride-*-instagram.md`:
   empieza con `# BORRADOR — NO PUBLICAR`, sigue la línea
   `_Procedencia: material sintético de prueba …_`, el post publica un solo
   fragmento con su `Fuente: pie-sint-… / frg-sint-… (, página N)
   (expresión)` y cierra con la lista `REFERENCIAS NO UTILIZADAS` de los
   fragmentos descartados, con su motivo, fuera del texto publicable.
2. `salida/post-efemeride-demo/logs/ejecuciones.jsonl`: una línea
   `PENDIENTE_VALIDACION` / `borrador_generado` con `data_origin`,
   `hv_consulta` (tema hasheado cuando se pasa `--tema`), `hv_fragmentos`,
   `hv_piezas_fuente`, `hv_contract_status` y las versiones de contrato,
   prompt y renderer; y una línea `INCOMPLETA` / `material_insuficiente`
   del caso sin material.
3. `salida/post-efemeride-demo/estado-decisiones/decisiones-pendientes.jsonl`:
   el objeto `efemeride-…-instagram` declarado `publicacion` pendiente.
4. Variantes: `--canal linkedin` (otro prompt y CTA), `--precision dia` con
   `--desde 1926-08-07 --hasta 1926-08-07` (la efeméride se nombra como día
   exacto porque la consulta lo declara), `--tema` (acota la búsqueda; en
   el log sólo queda `tema_hash`).

La suite focalizada cubre el mismo recorrido más los bordes —gates,
reintento, canal inválido, consulta inválida, puerto que devuelve basura,
fuente no renderizable, política incompatible, destino caído—:

```bash
uv run pytest -q tests/test_posts_efemeride.py
```
