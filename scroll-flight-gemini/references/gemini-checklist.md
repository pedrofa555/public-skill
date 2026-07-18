# Checklist manual no app Gemini

## Rota API-first

Se `GEMINI_API_KEY` estiver configurada, a invocação da skill implica autorização para usar a API. Ler [api-adapter.md](api-adapter.md), executar o `--dry-run` e gerar stills e clipes em fases separadas. Nunca registrar a chave. Sem chave, seguir o fluxo manual.

## Antes de gerar

1. Confirmar que o usuário está conectado ao app Gemini com a conta desejada.
2. Confirmar a cota diária informada pelo usuário; tratá-la como estimativa configurável.
3. Manter aberto o `manifest.json` e usar somente os caminhos declarados nele.
4. Criar um asset por vez para reduzir erros de nome e referência.

## Para cada still

1. Copiar o prompt completo, incluindo STYLE KEY e SAVE AS.
2. Anexar referências de marca fornecidas pelo usuário, quando necessárias.
3. Gerar a imagem no app Gemini.
4. Conferir sujeito, perspectiva, paleta, luz e espaço para copy.
5. Baixar o arquivo original, sem captura de tela.
6. Converter ou renomear para `still.png` sem reduzir a resolução manualmente.
7. Salvar exatamente em `./scroll-assets/scene-XX/still.png`.
8. Não substituir um still aprovado sem avisar o Codex, pois os prompts posteriores dependem dele.

Quando todos os stills estiverem salvos, voltar ao Codex e confirmar: “Salvei os stills”.

## Para cada clipe

1. Copiar o prompt completo da transição.
2. Anexar o still da cena atual e o still da próxima cena quando a interface permitir.
3. Se a interface aceitar apenas uma referência, anexar a cena atual e manter a descrição detalhada da cena final no prompt.
4. Gerar um único movimento de câmera, sem cortes internos.
5. Conferir estabilidade, identidade do sujeito, direção da luz e chegada à próxima composição.
6. Baixar o MP4 original.
7. Salvar exatamente em `./scroll-assets/transitions/scene-XX-to-YY.mp4`.

Quando todos os clipes estiverem salvos, voltar ao Codex e confirmar: “Salvei os clipes”.

## Se houver costura perceptível

1. Identificar a transição e descrever o corte: composição, luz, geometria ou identidade.
2. Pedir ao Codex o prompt de still intermediário daquela transição.
3. Gerar e salvar `scene-XX-to-YY-bridge.png` na pasta `transitions`.
4. Refazer o clipe afetado usando o bridge como referência adicional ou dividir a conexão em duas gerações, conforme a interface permitir.
5. Revalidar o MP4 substituído antes do build.

O crossfade do runtime reduz a percepção do corte, mas não transforma clipes independentes em frame-lock real.

## Se a cota acabar

1. Não aguardar obrigatoriamente a renovação.
2. Manter todos os stills aprovados.
3. Informar ao Codex quais clipes faltaram.
4. Autorizar o fallback estático completo com parallax e zoom.
5. Reconstruir em modo vídeo futuramente quando todos os clipes estiverem disponíveis.

## Google AI Studio opcional

Uma chave detectada localmente é separada da assinatura Google AI Pro. Só usar API após autorização explícita. Nunca colar a chave no chat, em prompts, no manifesto ou em logs.
