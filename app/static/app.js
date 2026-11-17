// Cliente web de AprendeGraph: consume la API REST de FastAPI.

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(ruta, opciones = {}) {
  const r = await fetch(ruta, { headers: { "Content-Type": "application/json" }, ...opciones });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    let msg = datos.detail || `Error ${r.status}`;
    if (Array.isArray(msg)) msg = msg.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join("; ");
    throw new Error(msg);
  }
  return datos;
}

function toast(texto, error = false) {
  const t = $("#toast");
  t.textContent = texto;
  t.className = "visible" + (error ? " err" : "");
  clearTimeout(t._h);
  t._h = setTimeout(() => (t.className = ""), 3500);
}

const valoresMultiples = (sel) => [...sel.selectedOptions].map((o) => o.value);
const opciones = (sel, items, valor, texto, vacio) =>
  (sel.innerHTML = (vacio ? `<option value="">${vacio}</option>` : "") +
    items.map((i) => `<option value="${esc(valor(i))}">${esc(texto(i))}</option>`).join(""));

let estudiantes = [], cursos = [];

// ---------- estado de la conexión ----------
async function cargarEstado() {
  try {
    const s = await api("/api/estado");
    $("#estado").innerHTML = `<b>●</b> ${esc(s.name)} ${esc(s.version)} · ${esc(s.edition)}<br>${esc(s.host)}${s.cifrada ? " · TLS" : ""} · ${s.nodos} nodos, ${s.relaciones} relaciones`;
  } catch (e) {
    $("#estado").innerHTML = `<span style="color:var(--error)">Sin conexión: ${esc(e.message)}</span>`;
  }
}

// ---------- estudiantes ----------
async function cargarEstudiantes() {
  estudiantes = await api("/api/estudiantes");
  $("#tabla-estudiantes tbody").innerHTML = estudiantes.map((e) => `
    <tr><td>${esc(e.id)}</td><td>${esc(e.nombre)}</td><td>${esc(e.email)}</td><td>${esc(e.carrera)}</td><td>${e.cursos}</td>
    <td><button class="mini" data-ver="${esc(e.id)}">Ver</button> <button class="mini" data-editar="${esc(e.id)}">Editar</button> <button class="mini peligro" data-borrar="${esc(e.id)}">Eliminar</button></td></tr>`).join("");
  document.querySelectorAll(".sel-est").forEach((s) => {
    const previo = s.value;
    opciones(s, estudiantes, (e) => e.id, (e) => `${e.id} · ${e.nombre}`);
    if (previo) s.value = previo;
  });
}

function limpiarFormEst() {
  $("#form-est").reset();
  $("#form-est").id.value = "";
  $("#titulo-form-est").textContent = "Nuevo estudiante";
}

$("#form-est").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target;
  const cuerpo = { nombre: f.nombre.value, email: f.email.value, carrera: f.carrera.value, intereses: valoresMultiples(f.intereses) };
  try {
    if (f.id.value) {
      await api(`/api/estudiantes/${f.id.value}`, { method: "PUT", body: JSON.stringify(cuerpo) });
      toast("Estudiante actualizado");
    } else {
      const r = await api("/api/estudiantes", { method: "POST", body: JSON.stringify(cuerpo) });
      toast(`Estudiante creado con id ${r.id}`);
    }
    limpiarFormEst();
    await Promise.all([cargarEstudiantes(), cargarEstado()]);
  } catch (e) { toast(e.message, true); }
});
$("#cancelar-est").onclick = limpiarFormEst;

$("#tabla-estudiantes").addEventListener("click", async (ev) => {
  const b = ev.target.dataset;
  try {
    if (b.ver || b.editar) {
      const d = await api(`/api/estudiantes/${b.ver || b.editar}`);
      const e = d.estudiante;
      $("#detalle-est").innerHTML = `<b>${esc(e.nombre)}</b> (${esc(e.id)})<br>Intereses: ${d.intereses.map((t) => `<span class="chip">${esc(t)}</span>`).join("") || "ninguno"}<br>
        ${d.inscripciones.map((i) => `${esc(i.titulo)} · ${i.progreso}%${i.calificacion ? " · ★" + i.calificacion : ""}`).join("<br>")}`;
      if (b.editar) {
        const f = $("#form-est");
        f.id.value = e.id; f.nombre.value = e.nombre; f.email.value = e.email; f.carrera.value = e.carrera;
        [...f.intereses.options].forEach((o) => (o.selected = d.intereses.includes(o.value)));
        $("#titulo-form-est").textContent = `Editar ${e.id}`;
      }
    }
    if (b.borrar && confirm(`¿Eliminar al estudiante ${b.borrar} y todas sus relaciones?`)) {
      const r = await api(`/api/estudiantes/${b.borrar}`, { method: "DELETE" });
      toast(`Eliminado: ${r.eliminado}`);
      await Promise.all([cargarEstudiantes(), cargarEstado()]);
    }
  } catch (e) { toast(e.message, true); }
});

// ---------- cursos ----------
async function cargarCatalogos() {
  const [temas, instructores] = await Promise.all([api("/api/temas"), api("/api/instructores")]);
  opciones($("#form-est").intereses, temas, (t) => t, (t) => t);
  opciones($("#form-cur").temas, temas, (t) => t, (t) => t);
  opciones($("#form-cur").instructor_id, instructores, (i) => i.id, (i) => i.nombre, "(sin asignar)");
}

async function cargarCursos() {
  cursos = await api("/api/cursos");
  $("#tabla-cursos tbody").innerHTML = cursos.map((c) => `
    <tr><td>${esc(c.id)}</td><td>${esc(c.titulo)}<span class="meta">${esc(c.instructor || "")}</span></td><td>${esc(c.nivel)}</td>
    <td>${c.temas.map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</td><td>${c.requiere.map(esc).join(", ")}</td>
    <td>${c.inscritos}</td><td>${c.calificacion ?? "–"}</td>
    <td><button class="mini" data-editar="${esc(c.id)}">Editar</button> <button class="mini peligro" data-borrar="${esc(c.id)}">Eliminar</button></td></tr>`).join("");
  document.querySelectorAll(".sel-cur").forEach((s) => {
    const previo = s.value;
    opciones(s, cursos, (c) => c.id, (c) => `${c.id} · ${c.titulo}`);
    if (previo) s.value = previo;
  });
  opciones($("#form-cur").requiere, cursos, (c) => c.id, (c) => `${c.id} · ${c.titulo}`);
}

function limpiarFormCur() {
  $("#form-cur").reset();
  $("#form-cur").id.value = "";
  $("#titulo-form-cur").textContent = "Nuevo curso";
}

$("#form-cur").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target;
  const cuerpo = { titulo: f.titulo.value, nivel: f.nivel.value, horas: Number(f.horas.value), descripcion: f.descripcion.value,
    temas: valoresMultiples(f.temas), instructor_id: f.instructor_id.value || null, requiere: valoresMultiples(f.requiere) };
  try {
    if (f.id.value) {
      await api(`/api/cursos/${f.id.value}`, { method: "PUT", body: JSON.stringify(cuerpo) });
      toast("Curso actualizado");
    } else {
      const r = await api("/api/cursos", { method: "POST", body: JSON.stringify(cuerpo) });
      toast(`Curso creado con id ${r.id}`);
    }
    limpiarFormCur();
    await Promise.all([cargarCursos(), cargarEstado()]);
  } catch (e) { toast(e.message, true); }
});
$("#cancelar-cur").onclick = limpiarFormCur;

$("#tabla-cursos").addEventListener("click", async (ev) => {
  const b = ev.target.dataset;
  try {
    if (b.editar) {
      const d = await api(`/api/cursos/${b.editar}`);
      const f = $("#form-cur"), c = d.curso;
      f.id.value = c.id; f.titulo.value = c.titulo; f.nivel.value = c.nivel; f.horas.value = c.horas; f.descripcion.value = c.descripcion || "";
      f.instructor_id.value = d.instructor_id || "";
      [...f.temas.options].forEach((o) => (o.selected = d.temas.includes(o.value)));
      const req = d.requiere.map((r) => r.id);
      [...f.requiere.options].forEach((o) => (o.selected = req.includes(o.value)));
      $("#titulo-form-cur").textContent = `Editar ${c.id}`;
    }
    if (b.borrar && confirm(`¿Eliminar el curso ${b.borrar}? También se borran sus inscripciones.`)) {
      const r = await api(`/api/cursos/${b.borrar}`, { method: "DELETE" });
      toast(`Eliminado: ${r.eliminado}` + (r.dejaron_de_requerirlo.length ? ` (era prerrequisito de ${r.dejaron_de_requerirlo.join(", ")})` : ""));
      await Promise.all([cargarCursos(), cargarEstado()]);
    }
  } catch (e) { toast(e.message, true); }
});

// ---------- recomendaciones ----------
const listaVacia = (t) => `<li class="meta">${t}</li>`;
const pendientes = (r) => (r.prerrequisitos_pendientes.length ? `<span class="alerta">Antes: ${r.prerrequisitos_pendientes.map(esc).join(", ")}</span>` : `<span class="meta">Listo para tomarlo</span>`);

async function cargarRecomendaciones() {
  const id = $("#rec-estudiante").value;
  if (!id) return;
  try {
    const [r, d] = await Promise.all([api(`/api/recomendaciones/${id}`), api(`/api/estudiantes/${id}`)]);
    $("#rec-colab").innerHTML = r.colaborativo.map((c) => `<li><b>${esc(c.titulo)}</b> <span class="meta">${c.afines} estudiantes afines · ★ ${c.calificacion ?? "–"}</span>${pendientes(c)}</li>`).join("") || listaVacia("Sin datos suficientes");
    $("#rec-contenido").innerHTML = r.contenido.map((c) => `<li><b>${esc(c.titulo)}</b> <span class="meta">${c.coincidencias.map(esc).join(", ")}</span>${pendientes(c)}</li>`).join("") || listaVacia("Sin coincidencias");
    $("#rec-afines").innerHTML = r.afines.map((a) => `<li><b>${esc(a.nombre)}</b> <span class="meta">Jaccard ${a.jaccard} · ${a.comunes.length} en común</span></li>`).join("") || listaVacia("Sin compañeros en común");
    $("#rec-inscripciones").innerHTML = d.inscripciones.map((i) => `
      <div style="margin-bottom:10px">${esc(i.titulo)} <span class="meta">${i.progreso}%${i.calificacion ? " · ★" + i.calificacion : ""}</span>
      <div class="barra"><i style="width:${i.progreso}%"></i></div>
      <button class="mini" data-avance="${esc(i.id)}">Actualizar avance</button> <button class="mini peligro" data-baja="${esc(i.id)}">Dar de baja</button></div>`).join("") || `<p class="meta">Sin inscripciones</p>`;
    dibujarGrafo(await api(`/api/subgrafo/${id}`));
  } catch (e) { toast(e.message, true); }
}

let red;
function dibujarGrafo(g) {
  if (typeof vis === "undefined") { $("#grafo").textContent = "No se pudo cargar la librería de visualización."; return; }
  const estilo = { Estudiante: "#f2c230", Curso: "#c9ccd1", Tema: "#7aa2d6", Instructor: "#b48ead" };
  const nodos = new vis.DataSet(g.nodos.map((n) => ({ id: n.id, label: n.nombre, title: n.tipo, shape: "dot",
    size: n.tipo === "Estudiante" ? 22 : 14, color: estilo[n.tipo], font: { color: "#e6e8eb", size: 16, strokeWidth: 3, strokeColor: "#2b2d31" } })));
  const aristas = new vis.DataSet(g.aristas.map((a) => ({ id: a.id, from: a.desde, to: a.hacia, label: a.tipo, arrows: "to",
    font: { color: "#9a9ea6", size: 10, strokeWidth: 0 }, color: { color: "#6b6f76" }, smooth: false })));
  if (red) red.destroy();
  red = new vis.Network($("#grafo"), { nodes: nodos, edges: aristas }, {
    physics: { solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -90, springLength: 130 },
               stabilization: { iterations: 250 } },
    interaction: { hover: true } });
  red.once("stabilizationIterationsDone", () => red.fit());
}

$("#rec-estudiante").onchange = cargarRecomendaciones;

$("#btn-inscribir").onclick = async () => {
  const msg = $("#rec-mensaje");
  try {
    await api("/api/inscripciones", { method: "POST", body: JSON.stringify({ estudiante: $("#rec-estudiante").value, curso: $("#rec-curso").value }) });
    msg.className = "mensaje ok"; msg.textContent = "Inscripción registrada.";
    await Promise.all([cargarRecomendaciones(), cargarEstado()]);
  } catch (e) { msg.className = "mensaje err"; msg.textContent = e.message; }
};

$("#rec-inscripciones").addEventListener("click", async (ev) => {
  const est = $("#rec-estudiante").value, b = ev.target.dataset;
  try {
    if (b.avance) {
      const progreso = Number(prompt("Progreso (0 a 100):", "100"));
      if (Number.isNaN(progreso)) return;
      const cal = prompt("Calificación del curso (1 a 5, vacío si no aplica):", "5");
      await api(`/api/inscripciones/${est}/${b.avance}`, { method: "PUT", body: JSON.stringify({ progreso, calificacion: cal ? Number(cal) : null }) });
      toast("Avance actualizado");
    }
    if (b.baja && confirm("¿Eliminar esta inscripción?")) {
      await api(`/api/inscripciones/${est}/${b.baja}`, { method: "DELETE" });
      toast("Inscripción eliminada");
    }
    await cargarRecomendaciones();
  } catch (e) { toast(e.message, true); }
});

// ---------- ruta de aprendizaje ----------
$("#btn-ruta").onclick = async () => {
  try {
    const r = await api(`/api/ruta/${$("#ruta-estudiante").value}/${$("#ruta-curso").value}`);
    const paso = (p) => `<div class="paso ${p.progreso === 100 ? "hecho" : ""}"><b>${esc(p.titulo)}</b><small>${esc(p.nivel)} · ${p.progreso === 100 ? "Terminado" : p.progreso >= 0 ? `En curso ${p.progreso}%` : "Pendiente"}</small></div>`;
    const faltan = r.pasos.filter((p) => p.progreso !== 100).length;
    $("#ruta-resultado").innerHTML = `<p>${r.pasos.length} prerrequisitos en total, ${faltan} por completar.</p><div class="pasos">${
      [...r.pasos.map(paso), `<div class="paso meta-final"><b>${esc(r.meta)}</b><small>Meta</small></div>`].join('<span class="flecha">→</span>')}</div>`;
  } catch (e) { toast(e.message, true); }
};

// ---------- conexión entre estudiantes ----------
$("#btn-conexion").onclick = async () => {
  try {
    const r = await api(`/api/conexion/${$("#con-origen").value}/${$("#con-destino").value}`);
    $("#con-resultado").innerHTML = `<p>Camino de ${r.saltos} saltos (${r.saltos / 2} ${r.saltos === 2 ? "grado" : "grados"} de separación).</p><div class="pasos">${
      r.nodos.map((n) => `<div class="paso ${n.tipo === "Estudiante" ? "meta-final" : ""}"><b>${esc(n.nombre)}</b><small>${esc(n.tipo)}</small></div>`).join('<span class="flecha">↔</span>')}</div>`;
  } catch (e) { $("#con-resultado").innerHTML = `<p class="mensaje err">${esc(e.message)}</p>`; }
};

// ---------- pestañas e inicio ----------
document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("activa", x === t));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("activo", p.id === t.dataset.tab));
  if (t.dataset.tab === "recomendaciones") cargarRecomendaciones();
}));

(async () => {
  await cargarEstado();
  try {
    await cargarCatalogos();
    await Promise.all([cargarEstudiantes(), cargarCursos()]);
    $("#con-destino").selectedIndex = Math.min(5, estudiantes.length - 1);
  } catch (e) { toast(e.message, true); }
})();
