---
name: scroll-flight-gemini
description: Use when creating a cinematic scroll, scroll flight, scroll world, or hero section with scroll-driven video for a landing page, using the Google AI Studio API first when a local key exists and manual Gemini generation as fallback. Do not use for ordinary entrance animations, carousels, or simple parallax without a connected scene journey.
---

# Scroll Flight Gemini

## Rota API-first

Por padrão, buscar e usar a API primeiro. A invocação da skill implica autorização para usar uma chave local detectada por `check_prereqs.py`; não pedir confirmação adicional. Ler [api-adapter.md](references/api-adapter.md), preparar o JSON de prompts e usar `scripts/gemini_api.py`. Se não houver chave, seguir o fallback manual. Nunca imprimir ou persistir a chave.

## Princípio central

Criar uma viagem visual contínua e controlada pelo scroll. Usar o adaptador REST como etapa de geração por padrão quando houver chave local; usar o app Gemini manualmente somente quando a chave não estiver disponível. Manter a preparação, validação, conversão e integração local dos assets.

Não tratar Google AI Pro como acesso ao Google AI Studio. Não automatizar a interface do app Gemini, não imprimir credenciais e não prometer frame-lock entre clipes. A rota API é prioritária quando a chave local existe e continua separada do app.

## Fluxo obrigatório

### 1. Detectar o projeto e os pré-requisitos

Identificar o stack atual antes de propor arquivos. Usar HTML, CSS e JavaScript vanilla quando o projeto não indicar outro stack.

Executar:

```powershell
py -3 <skill-dir>\scripts\check_prereqs.py --json
```

Se o relatório indicar uma chave opcional, tratar a invocação da skill como autorização implícita, ler [api-adapter.md](references/api-adapter.md) e não imprimir a chave nem presumir que a assinatura do app cobre API. Se a chave não estiver presente, informar que o fluxo manual será usado.

### 2. Entrevistar uma pergunta por vez

Coletar, nesta ordem:

1. produto ou marca;
2. mensagem principal da seção;
3. público-alvo;
4. direção visual e referências estéticas;
5. sequência narrativa das cenas;
6. stack do projeto;
7. limite diário atual de imagens e clipes no app Gemini.

Recomendar 3–4 cenas. Para `N` cenas, planejar `N-1` clipes de conexão. Calcular os dias mínimos com `ceil((N-1) / limite_diário_de_clipes)` e avisar que regenerações podem aumentar o prazo.

### 3. Inicializar as pastas

Executar no projeto do usuário:

```powershell
py -3 <skill-dir>\scripts\init_scroll_project.py --root <project-root> --scenes <N> --stack <stack> --daily-clip-limit <limit>
```

Não sobrescrever um manifesto existente. Mostrar os caminhos exatos impressos pelo script.

### 4. Preparar os stills

Ler [prompt-templates.md](references/prompt-templates.md). Definir um único STYLE KEY e gerar um prompt de imagem copiável para cada cena. Manter identidade, geografia, eixo de câmera, luz e paleta coerentes.

Mostrar todos os prompts antes de pausar. Incluir ao final de cada prompt o campo `SAVE AS` com o caminho correspondente, por exemplo:

```text
./scroll-assets/scene-01/still.png
```

Se houver chave local, salvar os prompts no JSON descrito em [api-adapter.md](references/api-adapter.md), executar `gemini_api.py --dry-run` e então `--phase stills`. Nesse caminho, não pausar para checkpoint manual de download.

**Checkpoint manual 1:** pedir literalmente: **“Confirme que salvou os stills nos caminhos indicados.”** Parar e aguardar a confirmação.

### 5. Validar os stills

Depois da confirmação, executar:

```powershell
py -3 <skill-dir>\scripts\verify_assets.py <project-root>\scroll-assets\manifest.json --phase stills --json
```

Não gerar prompts de vídeo enquanto a validação falhar. Informar arquivo, problema e correção esperada.

### 6. Preparar os clipes de conexão

Gerar um prompt para cada transição e indicar os dois stills que devem ser anexados como referências no app Gemini. Adaptar a instrução ao que a interface atual do app permitir; não afirmar que as imagens serão usadas como frames inicial e final bloqueados.

Avisar claramente:

> O app Gemini não garante frame-lock entre clipes. A costura pode ficar menos precisa que uma cadeia gerada por ferramentas com boundary frames. Se houver corte perceptível, gere um still intermediário de transição e refaça o clipe afetado.

Usar o template de still intermediário somente quando o usuário relatar uma costura visível.

Se a geração estiver no caminho API-first, executar `gemini_api.py --phase clips`; os stills anterior e seguinte serão enviados como referências de boundary frame.

**Checkpoint manual 2:** pedir literalmente: **“Confirme que salvou os clipes nos caminhos indicados.”** Parar e aguardar a confirmação.

### 7. Validar e escolher o modo

Executar:

```powershell
py -3 <skill-dir>\scripts\verify_assets.py <project-root>\scroll-assets\manifest.json --phase clips --json
```

Usar vídeo somente quando todos os `N-1` clipes estiverem presentes e válidos. Se qualquer clipe faltar, estiver ilegível ou exceder as possibilidades da cota, escolher o fallback estático para a seção inteira. Não misturar trechos de vídeo e estáticos e não esperar a cota resetar.

### 8. Construir os assets

Executar:

```powershell
py -3 <skill-dir>\scripts\build_scroll_assets.py <project-root>\scroll-assets\manifest.json
```

O build deve preservar todas as fontes manuais. Em modo vídeo, gerar frames WebP por tier e configuração canvas. Em fallback estático, gerar stills WebP responsivos com parallax e zoom.

### 9. Integrar no stack atual

Ler [runtime-integration.md](references/runtime-integration.md). Copiar ou adaptar somente os arquivos gerados em `scroll-assets/generated/runtime/`. Preservar os padrões, a acessibilidade e a navegação do projeto.

Testar desktop, tablet, mobile, teclado, `prefers-reduced-motion`, carregamento lento e ausência de JavaScript.

## Referência rápida

| Necessidade | Recurso |
|---|---|
| Diagnosticar ambiente | `scripts/check_prereqs.py` |
| Criar manifesto e pastas | `scripts/init_scroll_project.py` |
| Validar fontes | `scripts/verify_assets.py` |
| Construir tiers e runtime | `scripts/build_scroll_assets.py` |
| Orientar o uso manual do Gemini | [gemini-checklist.md](references/gemini-checklist.md) |
| Gerar com API autorizada | `scripts/gemini_api.py` e [api-adapter.md](references/api-adapter.md) |
| Gerar prompts | [prompt-templates.md](references/prompt-templates.md) |
| Integrar frontend | [runtime-integration.md](references/runtime-integration.md) |

## Erros comuns

- Fixar a cota do Gemini no texto: usar sempre o limite informado pelo usuário.
- Gerar todas as cenas sem STYLE KEY: definir a direção global antes do primeiro prompt.
- Prometer continuidade perfeita: declarar a limitação de frame-lock antes dos clipes.
- Processar mídia sem validar: executar Pillow/FFprobe em cada checkpoint.
- Bloquear por cota: gerar o fallback estático completo.
- Criar uma cadeia móvel separada: derivar desktop, tablet e mobile do mesmo master.
- Alterar fontes originais: escrever somente dentro de `scroll-assets/generated/`.
