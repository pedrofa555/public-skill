# Templates de prompts para o app Gemini

Use os blocos como contratos de saída. Substitua os campos com o briefing aprovado e mantenha o mesmo STYLE KEY em toda a sequência.

## STYLE KEY global

```text
STYLE KEY
Brand/product: [nome e natureza do produto]
Visual language: [direção visual em uma frase]
World geometry: [espaço contínuo, escala e materiais]
Palette: [cores dominantes e acentos]
Lighting: [direção, temperatura e contraste]
Lens and camera axis: [lente aparente, altura e eixo]
Atmosphere: [névoa, partículas, profundidade]
Continuity anchors: [elementos que reaparecem entre cenas]
Aspect ratio: 16:9 master, safe central composition for responsive crops
Quality: high detail, clean edges, no embedded text, no watermark
```

## Prompt de still por cena

```text
Create one cinematic landing-page scene that belongs to a continuous visual journey.

STYLE KEY
[cole o STYLE KEY global sem alterações]

SCENE
Scene ID: [scene-01]
Narrative purpose: [o que esta cena comunica]
Primary subject: [produto, objeto ou ambiente]
Environment: [geografia e materiais]
Composition: [posição do sujeito e espaço negativo para copy]

CONTINUITY
Previous scene anchors: [elementos herdados ou “first scene”]
Next scene lead-in: [elemento espacial que aponta para a próxima cena]
Keep the same world scale, material language, palette and lighting direction.

CAMERA
[posição, altura, lente aparente, direção e distância]

LIGHT
[luz principal, preenchimento, atmosfera e contraste]

PALETTE
[cores e proporções]

NEGATIVE CONSTRAINTS
No text, no logos unless provided as a reference, no watermark, no duplicated objects,
no inconsistent perspective, no abrupt style change, no random extra characters.

SAVE AS
./scroll-assets/[scene-id]/still.png
```

## Prompt de vídeo entre duas cenas

Anexar os stills indicados pelo agente quando a interface do app permitir. Tratar ambos como referências visuais, não como boundary frames garantidos.

```text
Create a single continuous cinematic camera move connecting two established landing-page scenes.

STYLE KEY
[cole o mesmo STYLE KEY global]

REFERENCE IMAGES
Reference A: [scene atual / caminho]
Reference B: [próxima cena / caminho]
Use them to preserve identity, materials, palette, lighting and spatial geography.
They are visual references; avoid inventing a disconnected third environment.

START
Begin inside the composition and camera axis of Reference A.

CAMERA FLIGHT
[descreva uma trajetória simples: push, orbit curto, passagem por portal, descida ou avanço]
Keep motion readable, forward, stable and suitable for frame-by-frame scroll scrubbing.
Avoid cuts, teleportation, whip pans, flicker, morphing and sudden exposure changes.

END
Arrive naturally at the composition, subject scale and camera axis of Reference B.
Hold the final composition briefly and keep the subject stable.

CONTINUITY
Preserve [âncoras compartilhadas], world scale, light direction and color temperature.

NEGATIVE CONSTRAINTS
No cuts, no captions, no watermark, no duplicated subjects, no identity drift,
no frame interpolation artifacts, no camera shake, no unrelated scenery.

SAVE AS
./scroll-assets/transitions/[scene-a]-to-[scene-b].mp4
```

## Prompt de still intermediário

Usar somente quando a costura entre cenas apresentar um corte perceptível.

```text
Create one transition still exactly between the two attached scene references.

STYLE KEY
[cole o mesmo STYLE KEY global]

TRANSITION POSITION
Place the camera halfway along this path: [trajetória aprovada].
Blend only the spatial geography that must connect both scenes.
Preserve subject identity, materials, palette, lighting direction, lens and camera height.

COMPOSITION
The frame must work as the end target for the first half and the start reference for the second half.
Keep central motion readable and avoid new focal subjects.

NEGATIVE CONSTRAINTS
No text, no watermark, no unrelated objects, no style change, no distorted geometry.

SAVE AS
./scroll-assets/transitions/[scene-a]-to-[scene-b]-bridge.png
```

## Revisão antes de entregar prompts

- Confirmar que todos os blocos usam o mesmo STYLE KEY.
- Confirmar que cada cena tem uma função narrativa distinta.
- Confirmar que câmera, luz e geografia levam à cena seguinte.
- Confirmar que cada `SAVE AS` corresponde ao `manifest.json`.
- Explicar que consistência visual não equivale a frame-lock.
