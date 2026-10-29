import Link from "next/link";
export default function NotFound() {
  return (
    <section className="state">
      <span className="eyebrow">404 · FIN DEL RECORRIDO</span>
      <h1>Esta parada no existe.</h1>
      <p>Volvé al catálogo para encontrar tu próximo recorrido.</p>
      <Link className="button" href="/lineas">
        Explorar líneas
      </Link>
    </section>
  );
}
