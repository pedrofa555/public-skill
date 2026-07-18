# Integração do runtime

O build escreve os arquivos finais em `scroll-assets/generated/runtime/` e os tiers em pastas irmãs. Sirva a árvore `scroll-assets/generated/` sem alterar a relação entre essas pastas.

## HTML, CSS e JavaScript vanilla

1. Copiar a marcação de `scroll-flight.html` para a página.
2. Carregar `scroll-flight.css` no bundle ou com `<link>`.
3. Carregar `scroll-flight.js` após a marcação.
4. Montar a instância com o caminho público de `config.json`:

```html
<script>
  window.ScrollFlight.mount(
    document.querySelector("[data-scroll-flight-root]"),
    "/scroll-assets/generated/runtime/config.json"
  );
</script>
```

Substituir apenas o conteúdo de `[data-scroll-flight-content]` pela copy e pelos CTAs do projeto.

## React ou TanStack

Manter o runtime como arquivo externo. Montar e destruir no ciclo do componente:

```tsx
import { useEffect, useRef } from "react";

export function ScrollFlightSection() {
  const rootRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let instance: { destroy(): void } | null = null;
    window.ScrollFlight
      .mount(rootRef.current, "/scroll-assets/generated/runtime/config.json")
      .then((mounted) => {
        instance = mounted;
      });
    return () => instance?.destroy();
  }, []);

  return <section ref={rootRef} data-scroll-flight-root>{/* canvas e conteúdo */}</section>;
}
```

Carregar o script uma única vez pelo mecanismo já usado no projeto. Não duplicar o runtime em cada rota.

## Vue

Usar `onMounted` para chamar `mount` e `onBeforeUnmount` para chamar `destroy`. Manter a marcação do canvas dentro do template do componente e a configuração em URL pública.

## SSR genérico

Renderizar o HTML e o fallback no servidor. Chamar `mount` somente no cliente após `DOMContentLoaded` ou hidratação. O poster em `scene-01/still.png` deve continuar visível quando o JavaScript falhar.

## Verificações obrigatórias

- Servir WebP com o MIME correto.
- Confirmar que `config.json` e os frames não recebem a página HTML como resposta de fallback do roteador.
- Testar rolagem reversa e saltos rápidos de scroll.
- Testar viewport estreita e orientação paisagem.
- Testar `prefers-reduced-motion: reduce`.
- Confirmar que `destroy()` roda ao desmontar componentes.
- Medir o carregamento inicial: poster primeiro, frames próximos depois.
- Preservar conteúdo e CTA acessíveis acima do canvas.
