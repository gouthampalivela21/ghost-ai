document.querySelectorAll(".glass").forEach(card => {
  const observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        card.style.opacity = "1";
        card.style.transform = "translateY(0) scale(1)";
      }
    },
    { threshold: 0.4 }
  );

  observer.observe(card);
});