const sections = document.querySelectorAll(".reveal");

const observer = new IntersectionObserver(
  entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0) scale(1)";
        entry.target.style.transition =
          "opacity 1s ease, transform 1s cubic-bezier(0.16, 1, 0.3, 1)";
      }
    });
  },
  { threshold: 0.3 }
);

sections.forEach(sec => observer.observe(sec));