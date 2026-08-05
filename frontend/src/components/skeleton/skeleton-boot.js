/**
 * Early (non-module) boot — include in <head> before paint when possible:
 *   <script src="/src/components/skeleton/skeleton-boot.js"></script>
 * Re-shows a minimal overlay if the previous page marked a skeleton navigation.
 * Full styles/variants load with the ES module graph.
 */
(function () {
  try {
    var raw = sessionStorage.getItem("gf_skeleton_nav");
    if (!raw) return;
    var data = JSON.parse(raw);
    if (!data || Date.now() - (data.at || 0) > 8000) {
      sessionStorage.removeItem("gf_skeleton_nav");
      return;
    }
    var css =
      "#gfSkeletonBoot{position:fixed;inset:0;z-index:10000;background:var(--bg,#0b0d12);padding:1.5rem}" +
      "#gfSkeletonBoot .b{height:12px;border-radius:999px;background:rgba(128,128,128,.28);margin:.5rem 0;" +
      "animation:gfSkPulse 1.5s ease-in-out infinite}" +
      "#gfSkeletonBoot .box{height:80px;border-radius:8px;background:rgba(128,128,128,.28);" +
      "animation:gfSkPulse 1.5s ease-in-out infinite;margin:1rem 0}" +
      "#gfSkeletonBoot .g{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem}" +
      "@keyframes gfSkPulse{0%,100%{opacity:.55}50%{opacity:1}}";
    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
    var el = document.createElement("div");
    el.id = "gfSkeletonBoot";
    el.setAttribute("aria-busy", "true");
    el.innerHTML =
      '<div class="b" style="width:40%;height:18px"></div>' +
      '<div class="b" style="width:25%"></div>' +
      '<div class="g"><div class="box"></div><div class="box"></div><div class="box"></div><div class="box"></div></div>' +
      '<div class="box" style="height:200px"></div>' +
      '<div class="b" style="width:90%"></div><div class="b" style="width:70%"></div><div class="b" style="width:80%"></div>';
    function mount() {
      document.body.appendChild(el);
    }
    if (document.body) mount();
    else document.addEventListener("DOMContentLoaded", mount);
    window.__gfSkeletonBootEl = el;
  } catch (e) {
    /* ignore */
  }
})();
