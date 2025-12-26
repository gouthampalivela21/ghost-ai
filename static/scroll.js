gsap.registerPlugin(ScrollTrigger);

// Animate text on scroll
gsap.utils.toArray(".section").forEach(section => {
  gsap.from(section.querySelector(".title"), {
    opacity: 0,
    y: 80,
    duration: 1.2,
    scrollTrigger: {
      trigger: section,
      start: "top 70%",
    }
  });

  gsap.from(section.querySelector(".subtitle"), {
    opacity: 0,
    y: 40,
    delay: 0.2,
    duration: 1,
    scrollTrigger: {
      trigger: section,
      start: "top 70%",
    }
  });
});

// NAV ACTIVE LINK
const sections = document.querySelectorAll(".section");
const navLinks = document.querySelectorAll(".nav-link");

sections.forEach(section => {
  ScrollTrigger.create({
    trigger: section,
    start: "top center",
    end: "bottom center",
    onEnter: () => setActive(section.id),
    onEnterBack: () => setActive(section.id),
  });
});

function setActive(id) {
  navLinks.forEach(link => {
    link.classList.toggle(
      "active",
      link.getAttribute("href") === `#${id}`
    );
  });
}
gsap.registerPlugin(ScrollTrigger);

gsap.utils.toArray(".vp-section").forEach(section => {
  const card = section.querySelector(".glass");

  gsap.fromTo(
    card,
    {
      opacity: 0,
      scale: 0.85,
      y: 120,
      filter: "blur(20px)",
    },
    {
      opacity: 1,
      scale: 1,
      y: 0,
      filter: "blur(0px)",
      ease: "power3.out",
      duration: 1.6,
      scrollTrigger: {
        trigger: section,
        start: "top 75%",
        end: "top 40%",
        scrub: true,
      },
    }
  );
});
document.addEventListener("mousemove", e => {
  const x = (e.clientX / window.innerWidth - 0.5) * 20;
  const y = (e.clientY / window.innerHeight - 0.5) * 20;

  gsap.to(".glass", {
    rotateY: x,
    rotateX: -y,
    duration: 1,
    ease: "power2.out"
  });
});