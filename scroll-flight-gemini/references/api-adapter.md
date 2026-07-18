# Adaptador opcional do Google AI Studio

Use esta rota somente quando o usuário autorizar explicitamente a API e o processo detectar `GEMINI_API_KEY` ou `GOOGLE_API_KEY`. A assinatura Google AI Pro e a API têm quotas separadas.

O adaptador usa REST sem dependência externa. Ele gera imagens com Gemini Image e clipes assíncronos com Veo, anexando os stills das cenas anterior e seguinte como `firstFrame`/`lastFrame`. Isso melhora a costura, mas não garante identidade perfeita.

## Arquivo de prompts

Crie um JSON fora do manifesto, sem credenciais:

```json
{
  "scenes": {
    "scene-01": "prompt completo da cena 1",
    "scene-02": "prompt completo da cena 2"
  },
  "transitions": {
    "scene-01-to-02": "prompt completo da transição"
  }
}
```

## Execução

Faça primeiro um ensaio sem consumir quota:

```powershell
py -3 <skill-dir>\scripts\gemini_api.py <project-root>\scroll-assets\manifest.json <prompts.json> --dry-run
```

Com os prompts revisados, execute uma fase por vez:

```powershell
py -3 <skill-dir>\scripts\gemini_api.py <project-root>\scroll-assets\manifest.json <prompts.json> --phase stills
py -3 <skill-dir>\scripts\verify_assets.py <project-root>\scroll-assets\manifest.json --phase stills --json
py -3 <skill-dir>\scripts\gemini_api.py <project-root>\scroll-assets\manifest.json <prompts.json> --phase clips
py -3 <skill-dir>\scripts\verify_assets.py <project-root>\scroll-assets\manifest.json --phase clips --json
```

Depois execute `build_scroll_assets.py`. Se qualquer clipe faltar ou falhar, o build escolhe fallback estático para a seção inteira.

Nunca imprimir, registrar ou colocar a chave em manifesto, prompt, arquivo de saída ou mensagem de erro. Se a API retornar erro de quota, autenticação ou modelo indisponível, parar a fase atual e informar o erro sem repetir o segredo.
