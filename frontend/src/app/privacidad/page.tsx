import { Heading } from "@/components/ui";
export default function PrivacyPage() {
  return (
    <article className="privacy-copy">
      <Heading
        eyebrow="TU COLECCIÓN, TUS DATOS"
        title="Privacidad en Bondiala"
        text="Lo que registrás y quién puede verlo."
      />
      <h2>Lo que guardamos</h2>
      <p>
        Tu cuenta contiene un email, un nombre de usuario, tu nombre visible, un
        avatar opcional y tus preferencias. Cuando registrás un viaje guardamos
        el recorrido y las paradas de subida y bajada que elegiste, junto con la
        fecha de registro, tu progreso y los eventos de puntos.
      </p>
      <h2>Lo que compartís</h2>
      <p>
        Si activás el perfil público, la comunidad puede ver tu nombre visible,
        avatar, puntos, nivel, logros, métricas agregadas y progreso por línea.
        Tu email y el historial detallado de viajes permanecen privados. Podés
        ocultar tu perfil desde Configuración para salir de las búsquedas y
        rankings.
      </p>
      <h2>Sin seguimiento continuo</h2>
      <p>
        Los viajes se registran manualmente. Bondiala no necesita GPS ni
        registra tu ubicación en segundo plano.
      </p>
      <h2>Sesión y apariencia</h2>
      <p>
        Usamos cookies para mantener tu sesión y proteger formularios. La
        preferencia de tema se guarda también en tu dispositivo. No almacenamos
        contraseñas ni credenciales de sesión en el almacenamiento local del
        navegador.
      </p>
      <h2>Mapas y avatares</h2>
      <p>
        Al consultar mapas, tu navegador se conecta al proveedor cartográfico
        configurado, que recibe la información habitual de una solicitud web.
        Los avatares alojados externamente se cargan desde el enlace que elijas.
      </p>
      <h2>Control de tu cuenta</h2>
      <p>
        Podés modificar tu nombre, avatar, apariencia y visibilidad desde
        Configuración y recuperar la contraseña con tu email. Para solicitar la
        eliminación de la cuenta, contactá al administrador de la instancia. La
        eliminación debe incluir tus viajes, relaciones y datos de progreso
        asociados.
      </p>
    </article>
  );
}
