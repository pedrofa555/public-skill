(function scrollFlightRuntime(global) {
  "use strict";

  const clamp = (value, minimum, maximum) =>
    Math.min(maximum, Math.max(minimum, value));

  class ScrollFlight {
    constructor(root, config, configUrl) {
      if (!root) throw new Error("ScrollFlight root element is required");
      this.root = root;
      this.config = config;
      this.configUrl = new URL(configUrl, document.baseURI);
      this.canvas = root.querySelector("[data-scroll-flight-canvas]");
      this.context = this.canvas.getContext("2d", { alpha: false });
      this.fallback = root.querySelector("[data-scroll-flight-fallback-image]");
      this.reducedMotion = global.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;
      this.tier = null;
      this.frames = [];
      this.cache = new Map();
      this.inflight = new Map();
      this.active = false;
      this.raf = 0;
      this.progress = 0;
      this.direction = 1;
      this.destroyed = false;
      this.boundScroll = this.onScroll.bind(this);
      this.boundResize = this.resize.bind(this);
      this.observer = null;
    }

    async init() {
      this.tier = this.selectTier();
      this.frames = this.buildFrameIndex();
      this.root.style.setProperty(
        "--scroll-flight-screens",
        String(this.config.scrollScreens || 3)
      );
      this.root.dataset.scrollFlightMode = this.config.mode;
      this.setFallbackPoster();
      this.resize();

      if (this.reducedMotion) {
        this.drawStatic(0);
        this.root.classList.add("is-ready");
        return this;
      }

      this.observer = new IntersectionObserver(
        (entries) => this.onIntersect(entries),
        { rootMargin: "100% 0px" }
      );
      this.observer.observe(this.root);
      global.addEventListener("scroll", this.boundScroll, { passive: true });
      global.addEventListener("resize", this.boundResize, { passive: true });
      this.onScroll();
      this.root.classList.add("is-ready");
      return this;
    }

    selectTier() {
      const preferred = global.innerWidth <= 768
        ? "mobile"
        : global.innerWidth <= 1280
          ? "tablet"
          : "desktop";
      return (
        this.config.tiers.find((tier) => tier.name === preferred) ||
        this.config.tiers[0]
      );
    }

    buildFrameIndex() {
      if (this.config.mode !== "video") return [];
      const frames = [];
      for (const [segmentIndex, transition] of this.tier.transitions.entries()) {
        for (let frame = 1; frame <= transition.frameCount; frame += 1) {
          frames.push({
            segmentIndex,
            localIndex: frame - 1,
            frameCount: transition.frameCount,
            url: this.assetUrl(
              `${transition.path}/frame-${String(frame).padStart(6, "0")}.webp`
            ),
          });
        }
      }
      return frames;
    }

    assetUrl(path) {
      return new URL(`${this.config.assetBase || ""}${path}`, this.configUrl).href;
    }

    setFallbackPoster() {
      const firstScene = this.tier.scenes && this.tier.scenes[0];
      if (firstScene) this.fallback.src = this.assetUrl(firstScene.path);
    }

    onIntersect(entries) {
      this.active = entries.some((entry) => entry.isIntersecting);
      if (this.active) {
        this.scheduleRender();
        if (this.config.mode === "video" && this.frames.length) {
          this.prefetch(this.frameAtProgress(this.progress), this.direction);
        }
      }
    }

    onScroll() {
      if (this.destroyed) return;
      const rect = this.root.getBoundingClientRect();
      const travel = Math.max(1, this.root.offsetHeight - global.innerHeight);
      const nextProgress = clamp(-rect.top / travel, 0, 1);
      this.direction = nextProgress >= this.progress ? 1 : -1;
      this.progress = nextProgress;
      this.scheduleRender();
    }

    scheduleRender() {
      if (this.raf || (!this.active && !this.reducedMotion)) return;
      this.raf = global.requestAnimationFrame(() => {
        this.raf = 0;
        if (this.config.mode === "video" && this.frames.length) {
          this.drawVideo(this.progress);
        } else {
          this.drawStatic(this.progress);
        }
      });
    }

    frameAtProgress(progress) {
      return Math.round(clamp(progress, 0, 1) * Math.max(0, this.frames.length - 1));
    }

    async loadFrame(key, url) {
      const cached = this.cache.get(key);
      if (cached) {
        cached.touched = performance.now();
        return cached.resource;
      }
      if (this.inflight.has(key)) return this.inflight.get(key);

      const pending = (async () => {
        let resource;
        if ("createImageBitmap" in global) {
          const response = await fetch(url);
          if (!response.ok) throw new Error(`Frame request failed: ${response.status}`);
          resource = await global.createImageBitmap(await response.blob());
        } else {
          resource = await new Promise((resolve, reject) => {
            const image = new Image();
            image.decoding = "async";
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error(`Frame failed to load: ${url}`));
            image.src = url;
          });
        }
        this.cache.set(key, { resource, touched: performance.now() });
        this.enforceCacheLimit();
        return resource;
      })().finally(() => this.inflight.delete(key));

      this.inflight.set(key, pending);
      return pending;
    }

    prefetch(centerIndex, direction) {
      if (!this.frames.length || !this.active) return;
      const ahead = 12;
      const behind = 4;
      const start = direction >= 0 ? centerIndex - behind : centerIndex - ahead;
      const end = direction >= 0 ? centerIndex + ahead : centerIndex + behind;
      for (let index = Math.max(0, start); index <= Math.min(this.frames.length - 1, end); index += 1) {
        const frame = this.frames[index];
        this.loadFrame(frame.url, frame.url).catch(() => {});
      }
    }

    enforceCacheLimit() {
      const limits = { desktop: 96, tablet: 64, mobile: 40 };
      const limit = limits[this.tier.name] || 40;
      if (this.cache.size <= limit) return;
      const ordered = [...this.cache.entries()].sort(
        (left, right) => left[1].touched - right[1].touched
      );
      while (this.cache.size > limit && ordered.length) {
        const [key, entry] = ordered.shift();
        if (entry.resource && typeof entry.resource.close === "function") {
          entry.resource.close();
        }
        this.cache.delete(key);
      }
    }

    async drawVideo(progress) {
      const index = this.frameAtProgress(progress);
      const frame = this.frames[index];
      if (!frame) return;
      this.prefetch(index, this.direction);
      try {
        const resource = await this.loadFrame(frame.url, frame.url);
        this.drawFrame(resource, 1);
        const seam = this.config.crossfadeFrames || 0;
        const remaining = frame.frameCount - frame.localIndex - 1;
        const next = this.frames[index + remaining + 1];
        if (seam > 0 && remaining < seam && next && next.segmentIndex !== frame.segmentIndex) {
          const nextResource = await this.loadFrame(next.url, next.url);
          this.drawFrame(nextResource, 1 - remaining / seam);
        }
      } catch (error) {
        console.warn("ScrollFlight frame unavailable", error);
      }
    }

    async drawStatic(progress) {
      const scenes = this.tier.scenes || [];
      if (!scenes.length) return;
      const position = clamp(progress, 0, 1) * Math.max(0, scenes.length - 1);
      const index = Math.min(scenes.length - 1, Math.floor(position));
      const blend = position - index;
      const current = scenes[index];
      const next = scenes[Math.min(index + 1, scenes.length - 1)];
      try {
        const currentResource = await this.loadFrame(
          current.path,
          this.assetUrl(current.path)
        );
        this.drawFrame(currentResource, 1);
        if (next !== current && blend > 0) {
          const nextResource = await this.loadFrame(next.path, this.assetUrl(next.path));
          this.drawFrame(nextResource, blend);
        }
        this.root.style.setProperty(
          "--scroll-flight-static-scale",
          String(1 + progress * 0.08)
        );
        this.root.style.setProperty(
          "--scroll-flight-static-y",
          `${2 - progress * 4}%`
        );
      } catch (error) {
        console.warn("ScrollFlight still unavailable", error);
      }
    }

    drawFrame(resource, alpha) {
      const sourceWidth = resource.width || resource.naturalWidth;
      const sourceHeight = resource.height || resource.naturalHeight;
      if (!sourceWidth || !sourceHeight) return;
      const scale = Math.max(
        this.canvas.width / sourceWidth,
        this.canvas.height / sourceHeight
      );
      const width = sourceWidth * scale;
      const height = sourceHeight * scale;
      const x = (this.canvas.width - width) / 2;
      const y = (this.canvas.height - height) / 2;
      this.context.save();
      this.context.globalAlpha = alpha;
      this.context.drawImage(resource, x, y, width, height);
      this.context.restore();
    }

    resize() {
      if (!this.canvas) return;
      const ratio = Math.min(global.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.round(this.canvas.clientWidth * ratio));
      const height = Math.max(1, Math.round(this.canvas.clientHeight * ratio));
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
        this.scheduleRender();
      }
    }

    destroy() {
      this.destroyed = true;
      if (this.raf) global.cancelAnimationFrame(this.raf);
      if (this.observer) this.observer.disconnect();
      global.removeEventListener("scroll", this.boundScroll);
      global.removeEventListener("resize", this.boundResize);
      for (const entry of this.cache.values()) {
        if (entry.resource && typeof entry.resource.close === "function") {
          entry.resource.close();
        }
      }
      this.cache.clear();
      this.inflight.clear();
    }

    static async mount(root, configUrl = "./config.json") {
      if (!root) return null;
      const response = await fetch(configUrl);
      if (!response.ok) throw new Error(`ScrollFlight config failed: ${response.status}`);
      const config = await response.json();
      const instance = new ScrollFlight(root, config, configUrl);
      return instance.init();
    }
  }

  global.ScrollFlight = ScrollFlight;
})(window);
