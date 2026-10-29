// Instalación PWA sin cachear sesiones, viajes ni respuestas privadas.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", event => {
  if (event.request.mode === "navigate") event.respondWith(fetch(event.request).catch(() => new Response('<!doctype html><html lang="es-AR"><meta name="viewport" content="width=device-width"><title>Bondiala · Sin conexión</title><body style="font:18px system-ui;background:#FAFAF7;color:#17213A;padding:32px"><h1>Nos quedamos sin señal.</h1><p>Conectate a Internet para seguir bondiando. Tus viajes guardados siguen en tu cuenta.</p><button onclick="location.reload()">Volver a intentar</button></body></html>', { headers: { "Content-Type": "text/html; charset=utf-8" } })));
});
