const textos = {
  es: {
    brand: "MUEMOVIL · HOGAR EN ARMONÍA", title: "Imagina tu espacio, a tu manera", intro: "Encuentra el rincón donde cada mueble encaja con naturalidad. Comparte una foto de tu habitación y descubre una nueva forma de vivirla.", roomPreviewAlt: "Vista previa de la habitación", furniturePreviewAlt: "Vista previa del mueble",
    languageLabel: "Idioma", workspaceLabel: "Planificador de muebles", spaceTitle: "Prepara tu espacio", spaceIntro: "Usa una foto clara de la habitación.", roomPhoto: "Foto de la habitación", required: "Obligatoria", fileHint: "JPG, PNG o WEBP · hasta 16 MB", distanceLabel: "Distancia hasta el fondo de la habitación", distanceHint: "Mide desde donde tomaste la foto hasta la pared del fondo.",
    furnitureTitle: "Añade un mueble", furnitureIntro: "Sube una foto o indica sus medidas.", furniturePhoto: "Foto del mueble", optional: "Opcional", furnitureHint: "Las imágenes con fondo transparente ofrecen un mejor resultado.", width: "Ancho", depth: "Fondo", measureHint: "Indica ambas medidas o sube una imagen. Si solo usas imagen, se aplicarán medidas orientativas de 70 × 50 cm.", submit: "Encontrar el mejor lugar", privacy: "Tus imágenes se usan solo para preparar esta propuesta.", resultPlaceholder: "Tu propuesta aparecerá aquí", resultIntro: "Verás una sugerencia que respeta la distribución de tu habitación y los muebles existentes.", loadingTitle: "Preparando tu propuesta", loadingMessage: "Estamos revisando el espacio y las medidas.", loadingHint: "La primera propuesta puede tardar un poco más.", resultEyebrow: "TU PROPUESTA", resultAlt: "Escenario con la ubicación sugerida del mueble", footer: "Ideas para vivir mejor", backToForm: "Volver al planificador",
    validationFurniture: "Sube una foto del mueble o indica su ancho y fondo.", validationDimensions: "Indica tanto el ancho como el fondo del mueble.", failedTitle: "No se pudo preparar la propuesta", failedGeneric: "No se pudo completar la propuesta.", timeout: "La propuesta está tardando demasiado. Prueba con una imagen más pequeña.", rejected: "No se pudo procesar la solicitud.", qa: "No se pudo validar el resultado.",
    found: "Ubicación encontrada", none: "No se encontró espacio libre", noCollision: "SIN SOLAPAMIENTOS", review: "REVISAR ESCENARIO", foundSummary: "La propuesta se añade en una zona libre. Los muebles existentes permanecen en su posición.", noneSummary: "No se movieron los objetos existentes. Prueba con un mueble más pequeño o una foto con más espacio visible.", obstacles: "objetos detectados", walls: "zonas de pared delimitadas", estimatedDistance: "Distancia estimada", depthLimit: "Distancia indicada", genericError: "No se pudo completar la propuesta. Inténtalo de nuevo."
  },
  en: {
    brand: "MUEMOVIL · A HOME IN HARMONY", title: "Imagine your space, your way", intro: "Find the corner where every piece feels at home. Share a photo of your room and discover a fresh way to live in it.", roomPreviewAlt: "Room photo preview", furniturePreviewAlt: "Furniture photo preview", languageLabel: "Language", workspaceLabel: "Furniture planner", spaceTitle: "Set up your room", spaceIntro: "Choose a clear photo of your room.", roomPhoto: "Room photo", required: "Required", fileHint: "JPG, PNG or WEBP · up to 16 MB", distanceLabel: "Distance to the back of the room", distanceHint: "Measure from where you took the photo to the far wall.",
    furnitureTitle: "Add a piece of furniture", furnitureIntro: "Upload a photo or enter its dimensions.", furniturePhoto: "Furniture photo", optional: "Optional", furnitureHint: "Transparent backgrounds tend to give a better result.", width: "Width", depth: "Depth", measureHint: "Enter both dimensions or upload an image. Image only uses an approximate footprint of 70 × 50 cm.", submit: "Find the right place", privacy: "Your images are used only to prepare this suggestion.", resultPlaceholder: "Your suggestion will appear here", resultIntro: "See a suggestion that respects your room layout and existing furniture.", loadingTitle: "Preparing your suggestion", loadingMessage: "We are checking the space and dimensions.", loadingHint: "Your first suggestion may take a little longer.", resultEyebrow: "YOUR SUGGESTION", resultAlt: "Room with the suggested furniture placement", footer: "Ideas for better living", backToForm: "Back to planner",
    validationFurniture: "Upload a furniture photo or enter its width and depth.", validationDimensions: "Enter both the width and depth of the furniture.", failedTitle: "We could not prepare the suggestion", failedGeneric: "We could not complete the suggestion.", timeout: "This is taking too long. Try a smaller image.", rejected: "We could not process the request.", qa: "We could not validate the result.",
    found: "Placement found", none: "No clear space found", noCollision: "NO OVERLAP", review: "REVIEW ROOM", foundSummary: "The suggestion fits in a clear area. Existing furniture stays in place.", noneSummary: "Existing objects were not moved. Try smaller furniture or a photo with more open space.", obstacles: "objects detected", walls: "wall areas outlined", estimatedDistance: "Estimated distance", depthLimit: "Distance provided", genericError: "We could not complete the suggestion. Please try again."
  },
  fr: {
    brand: "MUEMOVIL · MAISON EN HARMONIE", title: "Imaginez votre espace, à votre façon", intro: "Trouvez le coin où chaque meuble s’intègre naturellement. Partagez une photo de votre pièce et découvrez une nouvelle façon de l’habiter.", roomPreviewAlt: "Aperçu de la photo de la pièce", furniturePreviewAlt: "Aperçu de la photo du meuble", languageLabel: "Langue", workspaceLabel: "Planificateur de meubles", spaceTitle: "Préparez votre pièce", spaceIntro: "Choisissez une photo nette de la pièce.", roomPhoto: "Photo de la pièce", required: "Obligatoire", fileHint: "JPG, PNG ou WEBP · 16 Mo maximum", distanceLabel: "Distance jusqu’au fond de la pièce", distanceHint: "Mesurez depuis l’endroit où la photo a été prise jusqu’au mur du fond.",
    furnitureTitle: "Ajoutez un meuble", furnitureIntro: "Importez une photo ou indiquez ses dimensions.", furniturePhoto: "Photo du meuble", optional: "Facultatif", furnitureHint: "Un fond transparent offre généralement un meilleur résultat.", width: "Largeur", depth: "Profondeur", measureHint: "Indiquez les deux dimensions ou importez une image. Sans dimensions, une empreinte indicative de 70 × 50 cm sera utilisée.", submit: "Trouver le meilleur emplacement", privacy: "Vos images servent uniquement à préparer cette proposition.", resultPlaceholder: "Votre proposition apparaîtra ici", resultIntro: "Découvrez un emplacement qui respecte la disposition de la pièce et les meubles existants.", loadingTitle: "Préparation de votre proposition", loadingMessage: "Nous vérifions l’espace et les dimensions.", loadingHint: "La première proposition peut prendre un peu plus de temps.", resultEyebrow: "VOTRE PROPOSITION", resultAlt: "Pièce avec l’emplacement suggéré du meuble", footer: "Des idées pour mieux vivre", backToForm: "Retour au planificateur",
    validationFurniture: "Importez une photo du meuble ou indiquez sa largeur et sa profondeur.", validationDimensions: "Indiquez la largeur et la profondeur du meuble.", failedTitle: "Impossible de préparer la proposition", failedGeneric: "Impossible de terminer la proposition.", timeout: "Le traitement prend trop de temps. Essayez une image plus petite.", rejected: "Impossible de traiter la demande.", qa: "Impossible de valider le résultat.",
    found: "Emplacement trouvé", none: "Aucun espace libre trouvé", noCollision: "SANS CHEVAUCHEMENT", review: "VÉRIFIER LA PIÈCE", foundSummary: "La proposition est placée dans une zone libre. Les meubles existants restent en place.", noneSummary: "Les objets existants n’ont pas été déplacés. Essayez un meuble plus petit ou une photo plus dégagée.", obstacles: "objets détectés", walls: "zones murales délimitées", estimatedDistance: "Distance estimée", depthLimit: "Distance indiquée", genericError: "Impossible de terminer la proposition. Veuillez réessayer."
  }
};

const form = document.querySelector("#formulario");
const scenarioInput = document.querySelector("#imagenEscenario");
const furnitureInput = document.querySelector("#imagenMueble");
const widthInput = document.querySelector("#anchoCm");
const depthInput = document.querySelector("#fondoCm");
let idiomaActual = "es";

function traducirPagina(idioma) {
  idiomaActual = textos[idioma] ? idioma : "es";
  const traducciones = textos[idiomaActual];
  document.documentElement.lang = idiomaActual;
  document.querySelectorAll("[data-i18n]").forEach((elemento) => {
    const texto = traducciones[elemento.dataset.i18n];
    if (texto) elemento.textContent = texto;
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((elemento) => {
    elemento.setAttribute("aria-label", traducciones[elemento.dataset.i18nAria]);
  });
  document.querySelectorAll("[data-i18n-alt]").forEach((elemento) => {
    elemento.alt = traducciones[elemento.dataset.i18nAlt];
  });
  document.querySelectorAll('input[type="file"]').forEach((entrada) => {
    entrada.setAttribute("aria-label", entrada.id === "imagenEscenario" ? traducciones.roomPhoto : traducciones.furniturePhoto);
  });
  document.querySelector("#limiteProfundidad").setAttribute("aria-label", traducciones.distanceLabel);
  const selectorIdioma = document.querySelector("#idioma");
  selectorIdioma.setAttribute("aria-label", traducciones.languageLabel);
  selectorIdioma.value = idiomaActual;
  document.title = `${traducciones.title} · Muemovil`;
}

document.querySelector("#idioma").addEventListener("change", (evento) => traducirPagina(evento.target.value));

function previewImage(fileInput, previewElement) {
  const file = fileInput.files[0];
  if (!file) {
    previewElement.hidden = true;
    previewElement.removeAttribute("src");
    return;
  }
  if (previewElement.dataset.objectUrl) URL.revokeObjectURL(previewElement.dataset.objectUrl);
  const imageUrl = URL.createObjectURL(file);
  previewElement.dataset.objectUrl = imageUrl;
  previewElement.src = imageUrl;
  previewElement.hidden = false;
}

scenarioInput.addEventListener("change", () => previewImage(scenarioInput, document.querySelector("#vistaEscenario")));
furnitureInput.addEventListener("change", () => previewImage(furnitureInput, document.querySelector("#vistaMueble")));

function validarMueble() {
  const tieneImagen = furnitureInput.files.length > 0;
  const tieneAncho = widthInput.value.trim() !== "";
  const tieneFondo = depthInput.value.trim() !== "";
  if (!tieneImagen && (!tieneAncho || !tieneFondo)) throw new Error(textos[idiomaActual].validationFurniture);
  if (tieneAncho !== tieneFondo) throw new Error(textos[idiomaActual].validationDimensions);
}

function mostrarCarga() {
  document.querySelector("#estadoInicial").hidden = true;
  document.querySelector("#resultado").hidden = true;
  document.querySelector("#cargando").hidden = false;
}

function mostrarError(mensaje) {
  document.querySelector("#cargando").hidden = true;
  document.querySelector("#resultado").hidden = true;
  const estado = document.querySelector("#estadoInicial");
  estado.hidden = false;
  estado.querySelector("h2").textContent = textos[idiomaActual].failedTitle;
  estado.querySelector("p").textContent = mensaje;
}

function mostrarResultado(resultado) {
  const idioma = textos[idiomaActual];
  document.querySelector("#cargando").hidden = true;
  document.querySelector("#estadoInicial").hidden = true;
  document.querySelector("#resultado").hidden = false;
  const colocado = resultado.estado === "colocado";
  document.querySelector("#tituloResultado").textContent = colocado ? idioma.found : idioma.none;
  const badge = document.querySelector("#marcaEstado");
  badge.textContent = colocado ? idioma.noCollision : idioma.review;
  badge.classList.toggle("no-space", !colocado);
  document.querySelector("#resumenResultado").textContent = colocado ? idioma.foundSummary : idioma.noneSummary;
  document.querySelector("#imagenResultado").src = resultado.imagen_anotada;

  const datos = document.querySelector("#datosResultado");
  datos.replaceChildren();
  const elementos = [
    `${resultado.cantidad_obstaculos} ${idioma.obstacles}`,
    `${resultado.cantidad_paredes} ${idioma.walls}`,
    resultado.colocacion
      ? `${idioma.estimatedDistance}: ${resultado.colocacion.profundidad_estimada_cm} cm`
      : `${idioma.depthLimit}: ${resultado.limite_profundidad_cm} cm`,
  ];
  elementos.forEach((texto) => {
    const chip = document.createElement("span");
    chip.className = "detail-chip";
    chip.textContent = texto;
    datos.append(chip);
  });
  document.querySelector("#notaResultado").textContent = [resultado.nota_profundidad, resultado.advertencia].filter(Boolean).join(" ");
}

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  try {
    validarMueble();
  } catch (error) {
    mostrarError(error.message);
    return;
  }

  const boton = document.querySelector("#analizar");
  const controlador = new AbortController();
  const limiteCliente = window.setTimeout(() => controlador.abort(), 10 * 60 * 1000);
  boton.disabled = true;
  mostrarCarga();
  try {
    const respuesta = await fetch("/api/analizar", { method: "POST", body: new FormData(form), signal: controlador.signal });
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado.error || textos[idiomaActual].rejected);
    if (!resultado.qa?.correcto) throw new Error(textos[idiomaActual].qa);
    mostrarResultado(resultado);
  } catch (error) {
    mostrarError(error.name === "AbortError" ? textos[idiomaActual].timeout : (error.message || textos[idiomaActual].genericError));
  } finally {
    window.clearTimeout(limiteCliente);
    boton.disabled = false;
  }
});

traducirPagina("es");
