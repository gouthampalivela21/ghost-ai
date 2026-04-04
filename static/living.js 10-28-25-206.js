document.querySelectorAll(".glass").forEach(card => {
  card.addEventListener("mousemove", e => {
    const r = card.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 100;
    const y = ((e.clientY - r.top) / r.height) * 100;

    card.style.setProperty("--x", `${x}%`);
    card.style.setProperty("--y", `${y}%`);
    card.style.setProperty("--glow", "1");
  });

  card.addEventListener("mouseleave", () => {
    card.style.setProperty("--glow", "0");
  });
});