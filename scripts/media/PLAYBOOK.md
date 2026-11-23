# Playbook de imágenes y videos con IA (Ardea Skin)

Guía práctica para generar las fotos de producto, las imágenes de categoría y los videos explicativos
de la tienda, con los errores que ya encontramos y cómo se resolvieron. Si vas a crear medios
nuevos, lee primero la sección de errores conocidos.

Última actualización: 2026-11-20. Las 3 categorías de la demo (limpiadores, sérums y mascarillas)
tienen portada y video.

---

## 1. El flujo completo

```
categories.json  ──►  imagen de portada (Nano Banana Pro)  ─┐
 (textos, tomas,      clip de 15 s (Gemini Omni)            ├─► revisión manual ─► Shopify Files ─► category-media.json ─► web
  subtítulos, voz)    voz por subtítulo (Gemini TTS)        │
                      montaje (ffmpeg)  ────────────────────┘
```

| Paso | Herramienta | Comando | Costo aprox. |
|---|---|---|---|
| Foto de producto 1:1 | `gemini-3-pro-image` (Nano Banana Pro), 2K | `python scripts/images/generate_product_image.py <handle> --ref <aprobada>` | 0,14 USD |
| Imagen de portada 16:9 | `gemini-3-pro-image`, 2K | `python scripts/media/generate_category_media.py <slug> hero` | 0,14 USD |
| Clip de video 15 s | `gemini-omni-1.2-flash`, 1080p | `python scripts/media/generate_category_media.py <slug> clip` | 1,56 USD (720p: 1,04) |
| Voz | `gemini-3.8-flash-tts` | `python scripts/media/generate_category_media.py <slug> voice` | < 0,01 USD |
| Montaje | ffmpeg (vía `pip install imageio-ffmpeg`) | `python scripts/media/generate_category_media.py <slug> assemble` | gratis |
| Subida al CDN | Shopify Files | `python scripts/shopify/upload_files.py <slug> --hero … --poster … --video …` | gratis |

**Una categoría completa cuesta ≈ 1,70–1,90 USD.** Precios verificados el 2026-11-20 en
`aistudio.google.com/docs/pricing`. Google duplica el precio de la voz desde el 1 de enero de 2027.

### Dónde vive cada cosa

- **Textos de la página y guion del video:** `apps/web/src/content/categories.json`. Página y video
  salen del mismo archivo para que no se desincronicen.
- **URLs de los medios publicados:** `apps/web/src/content/category-media.json` (lo escribe `upload_files.py`).
- **Fotos de producto aprobadas:** `scripts/images/approved.json`. Los archivos están en
  `scripts/images/out/` y no se suben a git.
- **Salidas de video:** `scripts/media/out/<slug>/` (no se suben a git).
- **Tipografías para subtítulos:** `scripts/media/fonts/` (Fraunces e Inter, licencia OFL).

---

## 2. Errores conocidos y su solución

Cada error se encontró generando de verdad. El "cómo se detectó" importa: casi ninguno daba un
mensaje de error, el resultado simplemente salía mal.

### Voz (TTS)

**V1. El modelo de voz lee en voz alta las instrucciones de estilo.**
- **Síntoma:** una frase de 5 palabras duraba más de 4 s, y la narración completa 20-25 s.
- **Causa:** `gemini-3.8-flash-tts` no interpreta prefijos como "Read this in a calm voice…" ni
  "Say warmly and calmly:". Los lee como parte del texto.
- **Cómo se detectó:** transcribiendo el audio con `gemini-flash-latest`. La transcripción decía
  literalmente *"Say warmly and calmly, start on clean, toned skin"*.
- **Solución:** enviar **solo el texto que debe decirse**. El tono se controla eligiendo la voz
  (usamos `Aoede`), no con instrucciones.
- **Regla:** después de cambiar algo de la voz, transcribe siempre el resultado. No te fíes de la duración.

**V2. El audio ya llega como WAV.**
- **Síntoma:** duraciones raras y un posible clic al inicio.
- **Causa:** el modelo 3.8 devuelve `audio/wav` con cabecera; los modelos 2.5 devolvían PCM sin cabecera.
  Envolverlo otra vez en WAV metía la cabecera como si fuera sonido.
- **Solución:** si el `mimeType` contiene `wav` o los bytes empiezan por `RIFF`, guardarlo tal cual.

**V3. Cada frase trae silencio al principio y al final.**
- **Causa:** el modelo agrega relleno de silencio.
- **Solución:** recortar ambos extremos con ffmpeg (`silenceremove` + `areverse`, ya está en el script).

**V4. Una sola narración larga no coincide con las tomas.**
- **Síntoma:** las cuatro frases se decían en los primeros 7 s de un video de 15 s, así que la voz
  iba por delante de la imagen.
- **Solución:** **una frase por subtítulo** (campo `say` en `categories.json`). En el montaje cada
  frase se retrasa hasta el `from` de su subtítulo + 0,2 s. El script avisa si una frase dura más
  que su ventana.

**V5. La voz debe describir lo que se ve.**
- **Síntoma:** la voz decía "on your fingertips" mientras las gotas caían en la palma.
- **Solución:** después de generar el clip, mira los fotogramas y ajusta las frases `say` a lo que
  realmente muestra. Regenerar una frase cuesta céntimos; regenerar el clip, 1,56 USD.

### Video (Gemini Omni)

**C1. Veo no está disponible.**
- El modelo de video actual de esta API es **Gemini Omni 1.2 Flash** (`gemini-omni-1.2-flash`).
  Veo 3.1 Preview fue retirado.
- **No usa `generateContent`.** Usa la **Interactions API**: `POST /v1beta/interactions`.
- Cuerpo: `model`, `input` (lista de items `{"type":"image","data":<base64>,"mime_type":…}` y
  `{"type":"text","text":…}`) y `response_format`
  (`{"type":"video","aspect_ratio":"16:9","resolution":"1080p","duration":"15s","delivery":"uri"}`).
- Duración de 3 a 15 s. Se puede extender hasta 30 s en turnos de 3-10 s.
- El audio se genera siempre. No hay interruptor: se controla desde el prompt.
- Documentación: `https://aistudio.google.com/docs/omni`.

**C2. La URL de descarga viene completa.**
- **Síntoma:** el script falló *después* de generar (y cobrar) el video. Intentó leer como JSON lo
  que en realidad era el MP4.
- **Causa:** el campo `uri` trae `https://…/v1beta/files/<id>:download?alt=media`, no `files/<id>`.
- **Solución:** extraer el id con `re.search(r"files/([^:/?]+)", uri)`. Ya está corregido.
- **Si vuelve a fallar algo tras generar: NO regeneres.** La respuesta queda guardada en
  `out/<slug>/clip-response.json` y el archivo sigue disponible unas 48 h en
  `GET /v1beta/files/<id>:download?alt=media`. Descárgalo desde ahí.

**C3. El producto del video debe ser el nuestro.**
- **Solución:** pasar la foto aprobada del producto como imagen de referencia (`video.reference`
  en `categories.json`) y repetir en el prompt *"must look exactly like the product in the reference image"*.
- **Resultado:** el frasco salió idéntico, con "ARDEA" y el nombre del producto legibles.

**C4. Nada de texto generado dentro del video.**
- Pedimos *"Do not add any on-screen text, captions, subtitles or logos other than the ARDEA lettering"*.
  Los subtítulos los pone ffmpeg, con nuestra tipografía y en el momento exacto. El texto que genera
  un modelo puede salir con faltas o desalineado.

**C5. El audio del clip se usa como música de fondo.**
- Pedimos *"no dialogue, no voiceover, no singing; soft ambient room tone and a gentle, calm acoustic
  background track"*. En el montaje se baja al 30 % y la voz va encima, con normalización a -16 LUFS.

### Imágenes (Nano Banana Pro)

**I1. Lógica física: dos goteros.**
- **Síntoma:** en la portada de sérums, la mano sostenía un gotero y el frasco seguía con el suyo puesto.
- **Solución:** describir el estado de cada objeto sin ambigüedad: *"the bottle stands OPEN … its
  dropper is the one in her hand … there is only ONE dropper in the image"*.
- **Regla:** cuando una escena tiene un objeto en uso (gotero, tapa, tarro abierto), di dónde está cada pieza.

**I2. Describir el encuadre "por partes" produce collages.**
- **Síntoma 1:** pedir "espacio libre a la izquierda para el título" dio un rectángulo liso pegado a la izquierda.
- **Síntoma 2, peor:** corregirlo con *"the left third is the same out-of-focus background…"* dio
  **dípticos** (dos fotos pegadas con un corte vertical) en 3 de 4 portadas. Mencionar "el tercio izquierdo"
  hace que el modelo piense la imagen en partes.
- **Solución:** nunca describir el encuadre por zonas. Pedir **una sola fotografía**
  (`ONE_FRAME_TEXT` en el script: *"ONE single continuous photograph … not a collage, diptych … no vertical
  dividing lines … main subject slightly right of center"*) y resolver el área del texto con CSS (degradado).
- **Detector automático:** `seam_score()` mide en qué fracción de filas hay un borde fuerte en la misma
  columna. Calibrado con imágenes reales: dípticos 0,89–1,0, foto buena 0,24–0,34. Por encima de 0,6 el
  script imprime `WARNING` y la imagen no se usa.

**I3. Letras de dos colores en vidrio oscuro.**
- **Síntoma:** en el sérum de retinal (vidrio ámbar), "ARD" salió blanco y "EA" marrón.
- **Solución:** en envases oscuros, especificar *"ALL lettering … in one uniform solid ivory-cream color"*.

**I4. Aspecto "de laboratorio".**
- **Síntoma:** la primera foto parecía de farmacia: gotero estándar y etiqueta de papel pegada.
- **Solución (dirección de arte aprobada):**
  - vidrio grueso y pesado, de hombros redondeados;
  - **metal champán cepillado**;
  - letras **impresas sobre el envase**, sin pegatina;
  - pedestal de travertino, luz cálida de tarde, poca utilería.
- Está en `ART_DIRECTION` de `generate_product_image.py`.

**I5. Todos los envases iguales.**
- **Solución:** la marca es común, la escena no. Cada categoría tiene su envase y su escena
  (`PACKAGING` y `SCENES`), y los sérums se diferencian por el tono del vidrio o del líquido (`SERUM_TINTS`).

**I6. La foto de referencia puede contagiar la escena.**
- Al pasar la foto aprobada como referencia, aclarar: *"match its lettering style, champagne-gold
  finish, color grading … Do NOT copy its packaging shape or its set"*.

**I7. Revisar el texto letra por letra, recortando y ampliando la etiqueta.**
- El modelo escribe bien las etiquetas casi siempre, pero no siempre. Así se detectaron I3 y un
  "130 ML" en un tubo de 150 ml (portada de limpiadores). En la vista reducida no se distingue:
  **recorta la zona de la etiqueta, gírala si va en vertical y amplíala** antes de aprobar.

**I8. Un error de texto se corrige editando, no regenerando.**
- Se le pasa la imagen buena a Nano Banana Pro con *"Change only '130 ML' to '150 ML', in exactly the
  same font, size, color and position. Keep everything else in the image exactly the same."*
- Cuesta lo mismo (0,14 USD) pero conserva la composición aprobada.
- **Verificación:** diferencia píxel a píxel con la original. Salió una media de 1,4/255, solo en la zona de la etiqueta.

### Subida a Shopify Files

**S1. Los videos se cortan al subir.** Un MP4 de 6 MB falló con un tiempo de espera de 120 s y luego
con un corte SSL. Ahora: 900 s de espera para videos y un reintento automático.

**S2. Archivos huérfanos.** El script guardaba las URLs solo al final, así que cuando falló el video, la
portada y la miniatura ya subidas quedaron sin registrar y se duplicaron al reintentar. Ahora guarda
`category-media.json` después de cada archivo. Si vuelve a pasar, busca con
`files(query:"filename:<nombre>*")` y borra con `fileDelete` los que no estén en el JSON.

**S3. Shopify recodifica los videos a más peso.** Un MP4 de 2,2 MB (1080p) subido como `VIDEO` se sirvió
a 4,8 MB, y uno de 0,98 MB (720p) a 3 MB. Para videos de fondo que cargan en cada visita, sube tus propias
versiones como **archivo genérico** (`--raw-video brand-1080.mp4 brand-720.mp4`), que se sirven tal cual.
Para los tutoriales, que solo cargan cuando se ven, la versión de Shopify (1080/720/480) está bien.

### Video de marca (portada de la tienda)

- `python -c "import generate_category_media as g; g.brand()"` → un clip de 15 s con las **3 fotos de
  producto como referencia** (Omni admite hasta 6). Recorre mañana → tarde → noche, el mismo orden que la
  rutina, y termina con los tres productos juntos.
- `g.brand_web(<clip>)` → versiones web **sin pista de audio**, con fundido de entrada y salida al color
  arena de la página (`0xf5f0e8`) para que el bucle no dé saltos.
- En la web va en `autoPlay muted loop playsInline`. Si el visitante pidió menos movimiento
  (`prefers-reduced-motion`) o usa ahorro de datos, solo se muestra la miniatura.

### Reproducción automática de los tutoriales (`howto-video.tsx`)

- Arranca una vez cuando el reproductor se ve completo, se pausa con el 50 % o menos visible, y después
  solo el visitante lo reanuda.
- Los navegadores bloquean el autoplay **con sonido** si el visitante no ha interactuado: se intenta con
  sonido y, si falla, se reproduce en silencio con un botón "Tap for sound".
- **Probado con un navegador real** (Playwright, en `scripts/tests/video_behavior_test.py`, usando el Chrome
  instalado con `channel="chrome"`: el Chromium descargado por Playwright no coincidía con la versión del
  paquete).

### Cuentas y facturación

**F1.** Los modelos de imagen y video de Gemini tienen **cuota 0 en el nivel gratuito** (error 429
`limit: 0`). Hace falta activar la facturación. En Colombia es una recarga prepago; hicimos una de 100 000 COP.

**F2.** El costo de cada imagen se calcula desde `usageMetadata` (tokens de imagen × 120 USD/M +
texto y razonamiento × 12 USD/M + entrada × 2 USD/M). El script lo imprime. El de cada video, desde
`usage.output_tokens_by_modality` (1080p ≈ 8 688 tokens/s × 12 USD/M).

---

## 3. Lista de control para una categoría nueva

1. **Escribir el contenido en `categories.json`:** beneficios, pasos, guía de elección y `video`.
   En `video` van `reference` (handle del producto), `captions` con `from`/`to`/`text`/`say` y `shots` con tiempos.
   - 4 tomas de unos 3,5 s cada una. Las tomas en el prompt (`[0-4s] …`) deben coincidir con los subtítulos.
   - Frases `say` cortas, de 5 a 8 palabras: cada una debe durar menos que su ventana.
2. **Agregar la escena de portada** en `HERO_SCENES` (`generate_category_media.py`), describiendo el
   estado de cada objeto (I1) y el fondo continuo (I2).
3. `… <slug> voice` → **transcribir el resultado** y confirmar que dice exactamente el texto (V1).
4. `… <slug> hero` → revisar: un solo objeto de cada tipo, sin paneles, texto correcto.
5. `… <slug> clip` → extraer 4 fotogramas (uno por toma) y revisar el producto, las manos y la coherencia.
6. **Ajustar las frases `say`** a lo que muestra el clip (V5) y regenerar solo esas.
7. `… <slug> assemble` → revisar un fotograma con subtítulo y el volumen (media de unos -20 dB y
   picos por debajo de -1 dB: `ffmpeg -af volumedetect`).
8. `upload_files.py <slug> --hero … --poster … --video …` → actualiza `category-media.json`.
9. Compilar, desplegar (`bash infra/deploy.sh`) y comprobar que la página carga el video.

### Comandos útiles

```bash
FF=$(python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")

# Fotogramas de revisión, uno por toma
for t in 1.5 5.5 9.5 13.5; do "$FF" -y -loglevel error -ss $t -i clip.mp4 -frames:v 1 -vf scale=960:-1 f$t.jpg; done

# Silencios dentro de una voz (si dura demasiado)
"$FF" -i voice0.wav -af silencedetect=noise=-40dB:d=0.3 -f null - 2>&1 | grep silence_

# Volumen final
"$FF" -i final.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

Para transcribir una voz y verificarla: enviar el WAV a `gemini-flash-latest` con
*"Transcribe exactly what is spoken, word for word"*. Hay un ejemplo en el historial de esta sesión
y es fácil de rehacer con `generate_category_media.post()`.

---

## 4. Plantilla del guion de video

```json
"video": {
  "reference": "<handle del producto que aparece>",
  "captions": [
    { "from": 0.3,  "to": 3.8,  "text": "1  <paso corto>", "say": "<frase de 5-8 palabras>" },
    { "from": 3.9,  "to": 7.6,  "text": "2  <paso corto>", "say": "<frase>" },
    { "from": 7.7,  "to": 11.4, "text": "3  <paso corto>", "say": "<frase>" },
    { "from": 11.5, "to": 14.8, "text": "4  <paso corto>", "say": "<frase>" }
  ],
  "shots": "[0-4s] <toma 1> [4-8s] <toma 2> [8-12s] <toma 3> [12-15s] plano final del producto sobre travertino, lento acercamiento, letras ARDEA nítidas."
}
```

La última toma siempre es el producto solo, en reposo: de ahí sale la miniatura del video (el script
toma un fotograma 1,5 s antes del final).

---

## 5. Escena del portafolio (Iván en su escritorio)

- **Comando:** `python scripts/images/generate_portrait_scene.py C:/Users/Trollo/Desktop/ivan.jpeg --tag v2 [--extra "…"]`.
  Usa la foto real como **referencia de identidad**. Cuesta ≈ 0,14 USD por intento.
- **El prompt pide:**
  - una sola foto continua y cuadrada, con el sujeto centrado;
  - vista de tres cuartos hacia la cámara;
  - pantallas sin texto legible;
  - bordes que caen a casi negro (`#0b0d10`), para fundirse con la página sin borde duro.
- **Antes de aprobar:** compara la cara con la foto original (gafas, barba, forma de la cara). Revisa que no haya texto
  inventado en las pantallas.
- **Publicación:** la aprobada se exporta a `apps/web/public/portfolio/scene.webp` (1400 px, WebP calidad 84, unos 85 KB).
- **v1 (2026-11-21):** buen parecido. Pendientes:
  - el sujeto queda un poco a la izquierda;
  - las pantallas son blancas y brillantes; en modo oscuro encajarían mejor con la noche.

---

## 6. Videos explicativos del portafolio (primero: AI Agents, 2026-11-22)

**Flujo completo:**

| Paso | Comando |
|---|---|
| 1. Claqueta "By Ivan Dev" (2 s, código; sonido real CC0 en `sounds/`) | `python scripts/media/intro_clapper.py --reuse-frames` |
| 2. Tomas de personas (Gemini Omni, pantalla del celular nunca visible) | `python scripts/media/explainer_video.py ai-agents couch` |
| 3. Grabaciones reales de la tienda (Playwright) | `python scripts/media/record_store.py chat` / `restock` |
| 4. Voz (una frase por subtítulo, transcrita para verificar) | `python scripts/media/explainer_assemble.py voice` |
| 5. Montaje: marco de celular, zooms, títulos, tarjeta final, mezcla a -16 LUFS | `python scripts/media/explainer_assemble.py render` |
| 6. Publicación: video en Shopify Files y subtítulos .vtt | `python scripts/media/publish_explainer.py ai-agents` |

**Costo del primero:** unos $2.10 (3 tomas de Omni). La voz cuesta céntimos; la claqueta, las grabaciones y el montaje son gratis.

### Errores encontrados

**E1. Las grabaciones salían en baja resolución.**
- **Causa:** con emulación móvil, tanto el grabador de video de Playwright como el screencast de Chrome entregan píxeles CSS (390×844).
- **Solución:** un bucle de `Page.captureScreenshot` con `clip.scale = 2` (780×1688, ~14 fps), que se ensambla con sus tiempos reales.

**E2. Al hacer scroll, la parte de arriba salía en blanco.**
- **Causa:** el `clip` de CDP va en coordenadas del documento.
- **Solución:** sumar `scrollX/scrollY` en cada captura.

**E3. Subrayados rojos del corrector.**
- **Síntoma:** `--disable-spell-checking` empeoró las cosas, porque Chrome marcó todas las palabras al no tener diccionario de inglés.
- **Solución:** poner `el.spellcheck = false` solo en el campo de texto.

**E4. El celular a tamaño completo es ilegible.**
- **Causa:** ocupa un cuarto del ancho del cuadro, y en un reproductor de ~1000 px el texto queda en unos 5 px.
- **Solución:** zoom de unos 2× en cada momento de lectura, enfocado según posiciones medidas en la grabación (fracción de la altura de pantalla).

**E5. La página del producto seguía "Sold out" después de reponer.**
- **Causa:** la Storefront API de Shopify responde desde réplicas que no coinciden durante 15–40 s.
- **Solución:** la API refresca la caché de la tienda a los 0/10/25/45/90 s. El grabador espera con `_wait_for` a que la página muestre de verdad cada estado antes de filmarlo.

**E6. En pruebas, un movimiento de stock "no se aplicaba".**
- **Causa:** Shopify recuerda las claves `@idempotent`.
- **Solución:** usar una clave única por operación (`time.time_ns()`).

**E7. El agente de la tienda devolvía burbujas vacías.**
- **Causa:** el modelo escribía la respuesta junto a la llamada a herramienta y el código guardaba solo el último texto.
- **Solución:** se acumula el texto de todo el turno. Lo detectó la propia grabación del video.

**E8. Los subtítulos no se queman en el video.**
- Son pistas `<track>` nativas, con selector EN / ES / Off. El idioma por defecto sigue al navegador y se ven también en pantalla completa.
- Los navegadores solo descargan la pista activa: no lo tomes por un fallo en las pruebas.
- **Estilo:** `video.explainer::cue` y `size:78%` en cada cue.

**E9. Honestidad del guion.**
- "Seconds later" se cambió por "Moments later", porque la reposición tarda entre 5 y 40 s en verse.
- Cada pantalla que aparece es una grabación real.

**E10. Versiones con otra voz.**
- **Cómo se hacen:** `explainer_assemble.py all --lang es` reutiliza las mismas tomas y grabaciones; solo cambian la voz, los títulos y la tarjeta final.
- **Publicación:** `publish_explainer.py ai-agents --lang es`.
- **Un archivo por idioma:** los navegadores no cambian de pista de audio dentro de un mismo archivo (solo Safari). El reproductor cambia de archivo y conserva la posición.
- **Homófonos:** la transcripción de control también los detecta. "al agente" suena igual que "a la gente", así que se reformuló como "a nuestro agente".

## 7. Video general de la sección AI Agents (2026-11-22, en curso)

Guion aprobado: 6 tomas, unos 78 s, voz en inglés en primera persona ("I"), y versión en español.
Script de montaje: `scripts/media/overview_assemble.py`.

**Toma 1: Iván programando frente a las tres pantallas, con pantallas reales.**
1. **Fotograma inicial.** `explainer_video.py ai-agents-overview coding --still` (Gemini 3 Pro Image, unos $0,14).
   Usa como referencias la foto real de Iván y `scene.webp`, para que la oficina sea la misma de la portada.
   Se revisa el parecido antes de seguir.
2. **Clip de Omni de 6 s** con ese fotograma y la cámara fija ("LOCKED-OFF STATIC CAMERA"), unos $0,62.
   Deriva medida: 1 px como máximo, así que las pantallas no hay que seguirlas.
3. **Pantallas reales.** `overview_assemble.py coding` dibuja el contenido con Pillow (nuestro código escribiéndose y
   un chat de agente respondiendo) y lo coloca en perspectiva sobre las esquinas medidas en el cuadro 0.
   Después aplica desenfoque, el color de la toma, resplandor solo en lo brillante y grano.
   El acercamiento lento también lo hace este script, sobre la imagen ya compuesta.

**E11. La cara de Iván tapa el borde de la pantalla derecha.**
- **Solución:** una máscara por cuadro. La toma tiene un etalonaje turquesa, así que en las pantallas el azul siempre
  supera al rojo. La piel, la camisa e incluso la montura oscura de las gafas son más rojas que azules (`r > b + 8`).
  Por fila, todo lo que queda a la derecha del primer píxel "cálido" va por delante.
  El margen es de 3 px: con más, asoma el contenido inventado por la IA junto al perfil.
- **Error encontrado:** el recuadro de la máscara empezaba 4 px por encima del de la pantalla. El índice negativo dejó
  la máscara vacía y la pantalla tapaba la nariz. Calcula la máscara sobre el mismo recuadro que la pantalla.

**E12. Las pantallas reemplazadas salían lavadas.**
- **Causa:** el resplandor se calculaba sobre toda la imagen y aclaraba también el fondo.
- **Solución:** llevar el fondo del lienzo exactamente al fondo medido en la toma, aplicar el resplandor solo a los
  píxeles brillantes y comparar medianas con la pantalla original que no se toca (la izquierda).

**E13. `loudnorm` sube el audio a 96 kHz.** Añade `-ar 48000` a la salida.

**Toma 2: la dueña encierra en círculos, en su pizarra, las tareas donde la IA tiene sentido.**
- **Fotograma** con post-its completamente en blanco (`--still`, $0,14) y **clip de Omni de 10 s** con la cámara
  fija ($1,04). Ella dibuja los círculos alrededor de las notas, sin tapar el papel.
- **Posiciones:** los 15 post-its se detectan por color en el último cuadro (`wb_notes.json`).
  La deriva medida entre el primer y el último cuadro fue de 0 px.
- **Texto:** `overview_assemble.py whiteboard <en|es>` escribe las tareas con letra de rotulador (Ink Free, copiada
  de Windows a `fonts/`). Prueba primero en 2 líneas y, si no cabe, en 3.
  La tinta solo aparece donde se ve el papel: se compara cada píxel con el color del papel de esa nota en el cuadro
  limpio. Así el brazo, la mano o el rotulador la tapan de forma natural.
- **E14. El fin de cada círculo** se mide contando píxeles oscuros en un anillo alrededor de la nota. La manga oscura de
  ella también cuenta, así que se toma el cuadro después de la ÚLTIMA vez que el conteo baja del 85 %.
  Los distintivos turquesa salen en cadena cuando termina el último círculo; si no, aparecen encima de su mano.

**Toma 2 v2 (decisión del usuario): sin persona, círculos dibujados con código.**
- **E15. Omni no dibuja círculos creíbles:** se completaban solos o aparecían de golpe después de que ella pasara
  la mano. La toma se simplificó a un fotograma de la pizarra vacía (`whiteboard-empty --still`, $0,14, sin Omni).
- **Animación (`overview_assemble.py whiteboard`):**
  - textos fijos en las notas;
  - círculos trazo a trazo: un bucle que empieza arriba a la izquierda, va en sentido antihorario, se pasa un poco
    de su inicio, es algo ovalado y se abre en espiral, con antialiasing 3x;
  - cada distintivo aparece al cerrar su círculo;
  - acercamiento sobre el fotograma de 2752 px (siempre se reduce, nunca pierde nitidez) y grano en cada cuadro
    para que no parezca congelado.
- **Notas:** se detectan por color y se toma el recuadro por percentiles. Las esquinas extremas fallaban con una
  esquina doblada, y el texto salía diminuto y torcido.
- **Sonido:** ambiente de sala y trazos reales de rotulador, recortados del audio del primer clip de Omni
  (1,85–2,40 s y 3,30–3,90 s) y colocados en cada círculo (`whiteboard-room.wav`). Nada sintético.

**Toma 3: el cerebro de IA y las herramientas, hecha toda con código.**
- **Emblema:** un cerebro de circuitos turquesa sobre negro puro (`brain --still`, 1:1, $0,14), mezclado en modo
  pantalla para que el negro desaparezca. Late un poco con cada llegada.
- **Logos:** `scripts/media/logos.py` descarga los SVG de Simple Icons (CC0, versión fija) y los rasteriza en Chrome
  con Playwright a 512 px, en blanco y con fondo transparente. El script los presenta como fichas tipo app con el
  color de la marca; las marcas negras van en ficha clara.
- **E16. Logos retirados por sus marcas:** Excel, Adobe, OpenAI/ChatGPT, Slack y Google AI Studio ya no están en
  Simple Icons. NO se sacan de otras fuentes: salen como fichas con el nombre (uso nominativo).
- **Sincronía:** cada grupo entra cuando la voz lo nombra. Los tiempos de cada palabra se estimaron midiendo las
  pausas reales del audio de la voz y repartiendo proporcionalmente los caracteres entre ellas.
- **E17. Logos encimados en escalera:** pasaba con anillos a velocidades distintas y ángulos repartidos por igual.
  **Solución:** muestreo del punto más lejano sobre las 4 órbitas en pantalla, con tope por órbita (mínimo 132 px
  entre fichas), y todas las órbitas girando juntas. La entrada en espiral sigue con duraciones distintas
  (1,2–2,5 s).

**Toma 4: un dueño de tienda habla con su agente desde el celular.**
- **Fotograma** del dueño con el celular de espaldas a la cámara ($0,14) y **clip de Omni de 8 s** con cámara fija ($0,83).
- **Globos:** los mensajes salen del celular (usuario en blanco, agente en turquesa), con aparición elástica.
  Los anteriores suben y se desvanecen arriba. El texto del usuario se escribe mientras él teclea.
  Los emojis a color se dibujan con Segoe UI Emoji y `embedded_color=True` (Pillow 11).
- **Seguimiento:** el celular se sigue cuadro a cuadro con `cv2.matchTemplate` sobre su borde superior con las
  cámaras, con un suavizado de 7 cuadros. Se movía hasta 30 px.
- **Encuadre:** nunca encima de su cara (x ≥ 1405). El acercamiento se centra arriba (y = 140) para no sacar los
  globos de la pantalla. Una "|" en el texto fuerza el salto de línea, para que el número no quede separado de su nombre.

**Toma 5a: llegan peticiones de clientes, en primera persona, sobre la pantalla de Iván.**
- **Fotograma** por encima de su hombro (`requests --still`, con su foto y `coding-still.png` como referencias para
  que sea la misma oficina, $0,14). **Clip de Omni de 10 s** con cámara fija ($1,04), estirado a 12,3 s
  (`setpts=PTS/0.813`) para cubrir la voz. Con movimientos sutiles no se nota.
- **Mensajes:** avatar con iniciales genéricas (no son clientes reales) y burbuja blanca. Cada mensaje entra abajo,
  deslizándose, empuja a los demás hacia arriba, y el más viejo desaparece antes de tocar el borde.
  Ancho máximo de texto: 500 px, para no tapar su cabeza cuando gira hacia la pantalla.

**E18. Parecido de Iván y barba (correcciones del usuario).**
- **Síntoma:** en la 5a (desde atrás, sobre el hombro) no se parecía. Con poca cara visible el modelo inventa, y
  Omni lo deformaba más al girar la cabeza hacia la cámara.
- **Solución:** encuadre de PERFIL desde atrás y a su derecha (`requests-v2`). Referencias: su foto real y el
  fotograma de la toma 1, que sí se parece. En Omni: "NEVER turns his head toward the camera". Se generan 2
  variantes y él elige ANTES de animar.
- **Barba:** la quiere como en su foto real: bigote fino, barba corta en la barbilla y una línea fina en el borde de
  la mandíbula, con los cachetes limpios. Se pide como edición del fotograma aprobado (`coding-v2`).
  En el primer intento el modelo le afinó la cara; hay que añadir "Do NOT slim or reshape the face: keep the same
  full cheeks…".
- **Omni respetó el encuadre:** el clip nuevo de la toma 1 salió idéntico al anterior (0 px de diferencia), así que
  las esquinas de las pantallas medidas antes siguieron sirviendo. Compruébalo siempre comparando el cuadro 0.
- **Portada:** el usuario pidió dejar `scene.webp` como está.

**Toma 5b: las tres preguntas clave como títulos, todo con código.**
- Continúa la 5a sin corte. El último cuadro de `requests-composite-<lang>.mp4` se desenfoca (hasta 22 px) y se
  oscurece un 58 %, con un acercamiento lento alrededor del mismo punto que la 5a (que ya termina en 1,05).
- En `sample()`, los planos en `JOINED` no llevan fundido con el plano anterior.
- **Títulos:** Fraunces (la serif del sitio). Se usa el tamaño más grande que deja cada pregunta en una sola línea.
  La pregunta actual va en blanco, las anteriores bajan al 50 % y la última va en turquesa. Encima, un encabezado
  espaciado en turquesa.
- **Sincronía automática:** `speech_segments()` detecta los tramos hablados de la voz de cada idioma (pausas de al
  menos 0,1 s, umbral −38 dB). El 1.º es el encabezado y el 2.º, 3.º y 4.º son las preguntas. La versión en
  español se sincroniza sola.

**Toma 6: alejarse del video hasta un celular en el que una empresaria toca "Hire me on Upwork".**
- **Fotograma** con el celular en un soporte de escritorio, en horizontal y con la pantalla NEGRA ($0,14), y **clip de
  Omni de 7 s** con cámara fija ($0,73). Con el celular quieto no hace falta seguirlo; la pantalla se mide una vez.
- **E19. Primer clip descartado:** ella agarraba el borde superior del celular en vez de tocar el vidrio. El prompt que
  funcionó: mano desde abajo a la derecha, solo el índice extendido, toca el VIDRIO en la zona superior derecha
  "a little below its top edge", "never grabs the phone or its edge". En el segundo clip el dedo cae sobre el botón (4,0 s).
- **Composición (`viewer_shot`):**
  - Una cámara virtual sobre el clip (zoom y centro con fotogramas clave) hace el alejamiento, un plano abierto, el
    acercamiento al celular para el toque y la vuelta al plano abierto.
  - La pantalla se dibuja en el espacio de salida, así que siempre se ve nítida. Primero muestra el último cuadro de
    la 5b, con barras negras como un video a pantalla completa en horizontal, que se desenfoca al alejarse. Después,
    la página real capturada con Playwright (844×390 @3x).
- **E20. Alejamiento:** si el centro de la cámara se interpola en el espacio del clip, el celular salta a una esquina
  mientras el zoom sigue siendo enorme. Hay que interpolar la posición del celular EN LA SALIDA (del centro a su lugar
  final). En t=0, las esquinas del contenido coinciden con el cuadro, para empalmar con la 5b, y se ajustan a la
  pantalla real en 0,35 s.
- **E21. Lo que va delante de la pantalla:** sirve "no negro" con luminancia de 70 o más. Con 34, el reflejo tenue de su
  mano en el vidrio tapaba el botón. La máscara se dilata 3 px más allá del borde de la pantalla; si no, queda una línea
  negra sobre su mano en el borde.

**Publicado (2026-11-22) como video de la PORTADA, no de la sección.** El usuario cambió la portada: el círculo
queda a la izquierda y el video a la derecha (debajo en pantallas estrechas).
- **Toma 6:** el celular muestra la portada nueva con este mismo video en el reproductor (`capture_page()` contra
  localhost con `reduced_motion` para que no arranque solo, y CSS para ocultar el indicador de Next). La posición del
  botón se guarda junto a la captura.
- **Voz solo en inglés; el español va en subtítulos** (decisión del usuario). `overview_assemble.py final`:
  claqueta, 7 tomas, tarjeta "Ivan Dev" (`explainer_assemble.end_card()`), loudnorm, versiones de 1080 y 720, póster
  con el cerebro y los logos, y los subtítulos.
- **Subtítulos:** `write_cues()` (comando `cues`) parte cada frase de la voz en trozos de 84 caracteres como máximo,
  cortando en la puntuación. Una cláusula más larga se corta ANTES de una conjunción ("and", "y", "o"…) cerca de la
  mitad. Los límites se ajustan a las pausas reales de la voz.
- **Publicación:** `publish_explainer.py ai-agents-overview`. Tests: `scripts/tests/hub_intro_test.py` (15/15 en
  producción) y `explainer_playback_test.py`, que ahora mira solo el video de la sección (`article video.explainer`).
- **Costo total del video:** unos $8,20 de Gemini (Omni e imágenes), más céntimos de voz.
- **Subtítulos de la portada un 50 % más grandes dentro de la página** (`largeCues`, clase `cues-lg`: 1,08em; en pantalla
  completa vuelven a 0,72em). **E22:** el build de CSS (Tailwind v4 / Lightning CSS) DESCARTA en silencio reglas como
  `video.x.cues-lg::cue` y `…:fullscreen::cue`. Usa una variable en el elemento (`--cue-size`) que lee la regla base
  `video.explainer::cue { font-size: var(--cue-size, 0.72em) }`. Comprueba siempre la hoja de estilos servida.
- **E23. Los subtítulos los dibuja la página, no el navegador** (desde 2026-11-23). En el monitor del usuario (1280×1024,
  Chrome con aceleración por hardware en Windows), los subtítulos nativos DESAPARECÍAN en pantalla completa en cuanto
  se ocultaba la barra de controles, y volvían al mover el mouse. Chrome pasa el video a un plano directo de la GPU y
  los cues se quedan fuera. No se reproduce con Playwright, que usa otra configuración de GPU, aunque se ponga la ventana
  en pantalla completa real con CDP (`Browser.setWindowBounds` `windowState: fullscreen`). Solución en
  `explainer-video.tsx`:
  - La pista elegida queda en modo `hidden`: se carga y lanza `cuechange`, pero no se pinta. El texto va en un `<div
    data-cue>` encima del video, dentro de una caja 16:9.
  - Tamaño en `cqw`: `2.03cqw` es el estándar (5 % de la altura × 0.72) y `3.04cqw` el grande de la portada dentro de la
    página. Mínimos de 11 y 13 px.
  - El subtítulo sube a 74 px mientras la barra está visible (movimiento del puntero, ~2,6 s, o video en pausa) y baja al
    4,5 % cuando se oculta.
  - La pantalla completa la pide un botón propio (arriba a la derecha, o doble clic) sobre la CAJA del reproductor, no
    sobre el `<video>`. `controlsList="nofullscreen"` quita el botón nativo en Chrome/Edge.
  - Chrome deja ese botón nativo en gris. Se oculta con `video.explainer::-webkit-media-controls-fullscreen-button`
    dentro de un `<style href precedence>` del componente, porque el build de CSS también descarta ese pseudo-elemento
    (mismo problema que E22).
  - Respaldo: si el propio `<video>` entra en pantalla completa (botón de Firefox, iPhone con `webkitEnterFullscreen`),
    la pista pasa a `showing` y la pinta el navegador con la regla `::cue`.
  - Tests: `hub_intro_test.py` comprueba la pantalla completa (17/17) y `explainer_video_test.py` lee el texto de
    `[data-cue]`.
- **E24. iPhone: el video a veces se queda en 00:00 / 00:00** (2026-11-23). En Safari de iPhone el video quedaba
  "reproduciendo" sin que llegara ningún dato. El archivo y el CDN están bien: H.264 High, `moov` al principio y
  respuestas 206 correctas. Por eso el reproductor se protege solo:
  - Vigilante: si a los 3 s de darle a play no ha llegado ni un byte (ni un evento `progress`), recarga el archivo
    (`load()`) y vuelve a reproducir. Lo hace una vez por cada pulsación. Una descarga lenta pero en marcha se deja
    en paz.
  - En iOS el arranque automático va directamente sin sonido: Safari nunca acepta arrancar con sonido, y ese intento
    rechazado podía cruzarse con el toque del visitante.
  - La regla "pausar si se ve la mitad o menos" no actúa en pantalla completa, porque en iPhone la copia del
    reproductor en la página puede contar como fuera de vista.
  - Diagnóstico: con `?vdebug` en la dirección (p. ej. `ivanboot.dev/?vdebug`) aparece bajo el video un registro
    de eventos (readyState, networkState, errores, rechazos de play). Sirve para pedir un pantallazo desde un móvil
    sin herramientas de desarrollo.
  - Prueba local: un servidor que deja colgada la primera petición y redirige la segunda al CDN. Con eso, el video se
    recupera solo a los ~6 s.
  - Mi Browser (Xiaomi): pone su propio reproductor encima del video, que tapa nuestros subtítulos y botones, y su
    modo oscuro aclara los rellenos SVG del círculo. No se reproduce con el modo oscuro forzado de Chrome. Pendiente.
- **E25. Los videos y pósters del portafolio se sirven desde `ivanboot.dev/media/`** (2026-11-23). El registro
  `?vdebug` del iPhone del usuario mostró `ns=3` (NETWORK_NO_SOURCE) en menos de un segundo, también tras recargar.
  Safari descartaba el archivo de `cdn.shopify.com` y además no pintaba el póster: no era una descarga lenta.
  - Caddy (`infra/Caddyfile`, bloque `handle /media/*`) reenvía solo la carpeta de archivos de la tienda
    (`/s/files/1/0834/6445/4396/files/`) y quita las cabeceras propias del CDN (CSP `sandbox`, Report-To, NEL, Link).
    Los rangos (206) pasan tal cual.
  - `explainer-video.tsx` reescribe las URLs del CDN con `local()`; `portfolio-media.json` sigue guardando las
    originales.
  - Como Caddy monta el Caddyfile como archivo, tras desplegar un cambio hay que validarlo
    (`docker run --rm -v $PWD/infra/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine caddy validate --config
    /etc/caddy/Caddyfile --adapter caddyfile`) y reiniciar Caddy (`docker compose -f infra/docker-compose.yml
    restart caddy`). Un `reload` seguiría leyendo el archivo viejo.
  - `?vdebug` ahora también registra los errores de cada `<source>`, el póster y un `fetch` de prueba del video.
  - `section_ai_agents_test.py` necesita las dos URLs: `https://ivanboot.dev https://tienda.ivanboot.dev`.
- **E26. Causa real del fallo en iPhone: la caché de Safari** (2026-11-23). Con `?vdebug` el usuario comparó una
  primera visita, que reprodujo bien (póster ok, fetch 206, `playing`), con la recarga justo después, que falló:
  todas las `<source>` rechazadas en menos de un segundo (`ns=3`) aunque el póster sí cargaba.
  - Causa: el CDN de Shopify manda `Cache-Control: public, max-age=31557600`. Safari guarda los trozos (206) del
    video y en la recarga los reutiliza y los rechaza él mismo. Eso explica el "a veces sí, a veces no": la
    primera visita funciona y las siguientes no. No era el dominio (E25) ni el formato del archivo (H.264 High
    3.1, igual que el video de Ardea).
  - Arreglo:
    - Caddy envía los `.mp4` de `/media/` con `Cache-Control: no-store` (`header @video { … defer }`); los pósters
      conservan su caché.
    - Las URLs de video llevan `&c=2` (`localVideo()`), para que las copias que los iPhone ya guardaron con la URL
      vieja no se reutilicen nunca. Si alguna vez vuelve a pasar, basta con subir ese número.
    - Último recurso en `explainer-video.tsx`: si todas las fuentes se rechazan, o a los 3 s de play no ha llegado ni
      un byte, el reproductor recarga el video con una dirección nueva (`r=<marca de tiempo>`), como máximo 2 veces.
      Sustituye a la recarga simple de E24, que reutilizaba la misma copia rota.
  - Descartado: reproducir desde memoria (blob). El WebKit de Playwright en Windows no reproduce blobs ni siquiera
    en condiciones normales, así que no se puede verificar aquí.
  - Al validar el Caddyfile en el VPS, "Valid configuration" no siempre es la última línea de la salida: hay que
    buscarla con grep, no con `tail -1`.
- **E27. Lo que de verdad distinguía al portafolio: la lista `<source>` del HTML** (2026-11-23). El usuario aclaró
  que en su iPhone los videos de la tienda siempre funcionan. Esos videos salen del mismo CDN de Shopify, con la
  misma caché de un año y el mismo HTTP/3. Eso descarta las causas de E25 y E26 (dominio, caché) y la de HTTP/3
  (se probó a desactivarlo durante unos minutos).
  - Diferencia real: los reproductores de la tienda eligen el archivo en código y lo ponen como `src` tras montar.
    El del portafolio mandaba en el HTML dos `<source>` (1080 con `media`, 720), que Safari empezaba a cargar antes
    de que corriera el código de la página. En las recargas, la `<source>` de 720 fallaba unos 0,3 s después del
    play automático.
  - Cambio: `explainer-video.tsx` usa ahora un solo `src` elegido en el cliente (`useSyncExternalStore` con
    `(min-width: 1100px)`: 1080 en pantallas anchas, 720 en el resto) y vuelve a pedir las URLs directas del CDN,
    igual que la tienda.
  - Revertido: el proxy `/media/` y el `no-store` de Caddy (el Caddyfile vuelve a su versión original), y los
    cambios en los reproductores de la tienda, que no tenían ningún problema.
  - Se queda: la recarga con dirección nueva como último recurso, ahora en `lib/use-video-recovery.ts`. Ya no se
    dispara por error al cambiar a la voz en español: el elemento recién montado se comprueba 1,5 s después.
  - Pendiente: confirmación en el iPhone del usuario, recargando varias veces `ivanboot.dev/?vdebug`.
- **E28. CAUSA CONFIRMADA: las pistas `<track>` rompen el video en iPhone** (2026-11-23). Pruebas en el iPhone del
  usuario (iOS 18.7, Safari) con páginas servidas desde el VPS (`/opt/ivanboot/media`, en `ivanboot.dev/v/`):
  - `ivanboot.dev/v/` (`index.html`): el mismo archivo desde Shopify y desde el VPS, sin audio y recodificado.
    Todo ✅ las tres veces. No era Shopify ni el archivo.
  - `ivanboot.dev/v/prueba2.html`: el reproductor por partes. Con sonido ✅, con preload=metadata y póster ✅,
    con `<track src>` ❌ ERROR 4 (MEDIA_ERR_SRC_NOT_SUPPORTED, `ns=3` sin metadatos) y todo junto ❌. Con
    subtítulos creados por JavaScript (`addTextTrack` + `VTTCue`) ✅.
  - Arreglo: `lib/vtt.ts` (`parseVtt` y `attachSubtitles`) descarga el `.vtt` y crea las pistas por script.
    `explainer-video.tsx` ya no tiene ningún `<track>`. El resto, que lee `textTracks`, `cuechange`,
    hidden/showing y la superposición propia, no cambia.
  - Regla para cualquier video futuro: **nunca `<track src>`**. Los subtítulos siempre van con `attachSubtitles()`.
  - E24 a E27 fueron diagnósticos equivocados (caché, dominio, HTTP/3, lista `<source>`). Lo que queda de ellos
    (`src` único elegido en el cliente y recarga con dirección nueva como último recurso) es inofensivo y se queda.
  - La carpeta de videos del VPS se queda (Caddy `handle_path /v/*`, volumen `../media:/srv/media:ro`), para
    pruebas o para alojar videos fuera de Shopify. Ahora mismo solo contiene los archivos de esta prueba.
- **E29. iPhone: botones de la página encima del video** (2026-11-23). Safari en iPhone dibuja sus propios controles
  sobre la imagen y se lleva los toques de sus esquinas superiores: ampliar arriba a la izquierda, altavoz arriba a
  la derecha. "Tap for sound" (arriba a la izquierda) se veía, pero no respondía.
  - En iOS (`isIOS()` vía `useSyncExternalStore`), "Tap for sound" va debajo del video, encima de la leyenda.
  - En iOS no se muestra el botón propio de pantalla completa: Safari ya tiene el suyo y esa esquina es la del
    altavoz.
  - En escritorio y Android no cambia nada.
- **E30. Registro `?vdebug` retirado y Mi Browser** (2026-11-23).
  - Resuelto el iPhone (E28/E29), se quitó el registro en pantalla `?vdebug` de `explainer-video.tsx` y la opción
    `note` de `useVideoRecovery`. Las notas de E24 a E28 que lo mencionan describen cómo se diagnosticó.
  - Mi Browser (Xiaomi/Redmi) pintaba el círculo del inicio gris claro: su modo oscuro forzado aclara los rellenos
    SVG oscuros. El layout del portafolio declara `viewport = { colorScheme: "dark" }`
    (`<meta name="color-scheme" content="dark">`). Chromium y el WebView de Android no oscurecen páginas que
    dicen ser oscuras. La tienda es clara y no lleva esa etiqueta.
  - Mi Browser también pone su propio reproductor encima del video y tapa los subtítulos y botones de la página.
    Prueba en `ivanboot.dev/v/mi.html`: cuatro variantes (como ahora, sin controles del navegador, atributos x5,
    subtítulos nativos) más un sector del círculo. Pendiente de las capturas del usuario.
