/**
 * Script de respaldo en Node.js (ejecutar.js)
 * Ejecuta exactamente la misma arquitectura (Geometría 0-360° con recorte de huecos +
 * GRASP & 2-Opt + Evaluación de k autos) por si en esta PC no está instalado Python en el PATH.
 *
 * Uso: node ejecutar.js datos/ejemplo plan.json
 */
const fs = require("fs");
const path = require("path");

function distanciaManhattan(x1, y1, x2, y2) {
  return Math.abs(x1 - x2) + Math.abs(y1 - y2);
}

function calcularAngulosYDistancias(pedidos, depX, depY, umbralHueco = 12.0) {
  const resultado = pedidos.map((p) => {
    const px = Number(p.x);
    const py = Number(p.y);
    const pid = Number(p.id);
    const peso = Number(p.peso || 0);
    const dx = px - depX;
    const dy = py - depY;
    const distDep = distanciaManhattan(px, py, depX, depY);
    let angulo = 0.0;
    if (dx !== 0 || dy !== 0) {
      angulo = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360;
    }
    return {
      id: pid,
      x: px,
      y: py,
      peso,
      angulo: Number(angulo.toFixed(4)),
      angulo_util: 0.0,
      distancia_deposito: distDep,
    };
  });

  resultado.sort((a, b) => a.angulo - b.angulo || a.distancia_deposito - b.distancia_deposito);

  let acumulado = 0.0;
  if (resultado.length > 0) {
    resultado[0].angulo_util = 0.0;
    for (let i = 1; i < resultado.length; i++) {
      let salto = resultado[i].angulo - resultado[i - 1].angulo;
      if (salto > umbralHueco) salto = 0.001;
      acumulado += salto;
      resultado[i].angulo_util = Number(acumulado.toFixed(4));
    }
  }
  return resultado;
}

function dividirPorAnguloUtil(pedidos, k) {
  if (k === 1) return [pedidos.slice()];
  const minA = pedidos[0].angulo_util;
  const maxA = pedidos[pedidos.length - 1].angulo_util;
  const amp = maxA - minA;
  if (amp <= 1e-6) return dividirBalanceado(pedidos, k);
  const ancho = amp / k;
  const franjas = Array.from({ length: k }, () => []);
  for (const p of pedidos) {
    let idx = Math.floor((p.angulo_util - minA) / ancho);
    if (idx >= k) idx = k - 1;
    franjas[idx].push(p);
  }
  return franjas.filter((f) => f.length > 0);
}

function dividirBalanceado(pedidos, k) {
  const n = pedidos.length;
  const autos = Math.min(k, n);
  const base = Math.floor(n / autos);
  const resto = n % autos;
  const franjas = [];
  let ini = 0;
  for (let i = 0; i < autos; i++) {
    const fin = ini + base + (i < resto ? 1 : 0);
    franjas.push(pedidos.slice(ini, fin));
    ini = fin;
  }
  return franjas;
}

function costoDistanciaRuta(paradas, depX, depY) {
  if (!paradas.length) return 0;
  let d = distanciaManhattan(depX, depY, paradas[0].x, paradas[0].y);
  for (let i = 0; i < paradas.length - 1; i++) {
    d += distanciaManhattan(paradas[i].x, paradas[i].y, paradas[i + 1].x, paradas[i + 1].y);
  }
  d += distanciaManhattan(paradas[paradas.length - 1].x, paradas[paradas.length - 1].y, depX, depY);
  return d;
}

function busquedaLocal2Opt(ruta, depX, depY) {
  if (ruta.length <= 2) return ruta.slice();
  let mejor = ruta.slice();
  let mejorDist = costoDistanciaRuta(mejor, depX, depY);
  let mejoro = true;
  while (mejoro) {
    mejoro = false;
    for (let i = 0; i < mejor.length - 1; i++) {
      for (let j = i + 1; j < mejor.length; j++) {
        const rev = mejor.slice(i, j + 1).reverse();
        const cand = [...mejor.slice(0, i), ...rev, ...mejor.slice(j + 1)];
        const d = costoDistanciaRuta(cand, depX, depY);
        if (d < mejorDist) {
          mejor = cand;
          mejorDist = d;
          mejoro = true;
        }
      }
    }
  }
  return mejor;
}

function optimizarGrasp2Opt(franja, depX, depY) {
  if (franja.length <= 1) return franja.slice();
  let mejorRuta = null;
  let menorDist = Infinity;
  const alphas = [0.0, 0.15, 0.25, 0.35];

  let seed = 42;
  function rand() {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  }

  for (let it = 0; it < 35; it++) {
    const alpha = it === 0 ? 0.0 : alphas[it % alphas.length];
    const pendientes = franja.slice();
    const ruta = [];
    let ax = depX,
      ay = depY;
    while (pendientes.length > 0) {
      const dists = pendientes.map((p) => ({ d: distanciaManhattan(ax, ay, p.x, p.y), p }));
      const dMin = Math.min(...dists.map((x) => x.d));
      const dMax = Math.max(...dists.map((x) => x.d));
      const umbral = dMin + alpha * (dMax - dMin);
      const rcl = dists.filter((x) => x.d <= umbral).map((x) => x.p);
      const elegido = rcl[Math.floor(rand() * rcl.length)];
      ruta.push(elegido);
      pendientes.splice(pendientes.indexOf(elegido), 1);
      ax = elegido.x;
      ay = elegido.y;
    }
    const opt = busquedaLocal2Opt(ruta, depX, depY);
    const d = costoDistanciaRuta(opt, depX, depY);
    if (d < menorDist) {
      menorDist = d;
      mejorRuta = opt;
    }
  }
  return mejorRuta;
}

function resolver(carpeta, archivoSalida) {
  const mundo = JSON.parse(fs.readFileSync(path.join(carpeta, "mundo.json"), "utf8"));
  const pedidos = JSON.parse(fs.readFileSync(path.join(carpeta, "pedidos.json"), "utf8"));
  const vehiculos = JSON.parse(fs.readFileSync(path.join(carpeta, "vehiculos.json"), "utf8"));

  const depX = mundo.deposito_x ?? 0;
  const depY = mundo.deposito_y ?? 0;
  const minCuadra = mundo.min_por_cuadra ?? 3;
  const tServicio = mundo.tiempo_servicio ?? 5;
  const cCuadra = mundo.costo_por_cuadra ?? 3;
  const cVeh = mundo.costo_por_vehiculo ?? 60;
  const cMin = mundo.costo_por_minuto_total ?? 1;

  const pedidosOrdenados = calcularAngulosYDistancias(pedidos, depX, depY);

  console.log("=".repeat(68));
  console.log(`DATASET: ${carpeta}`);
  console.log(`Depósito: (${depX}, ${depY}) | Pedidos: ${pedidos.length} | Vehículos: ${vehiculos.length}`);
  console.log(
    `[Fase 1 - Geometría] Ángulo real: ${pedidosOrdenados[0].angulo}° a ${pedidosOrdenados[pedidosOrdenados.length - 1].angulo}° | Ángulo útil (sin huecos): ${pedidosOrdenados[pedidosOrdenados.length - 1].angulo_util}°`
  );
  console.log("-".repeat(68));
  console.log(" Autos (k) |  Distancia   |   Makespan   | Costo Autos  |  COSTO TOTAL ");
  console.log("-".repeat(68));

  let mejorPlan = null;
  let menorCosto = Infinity;
  let mejorK = 1;

  for (let k = 1; k <= vehiculos.length; k++) {
    const particiones = [
      dividirPorAnguloUtil(pedidosOrdenados, k),
      dividirBalanceado(pedidosOrdenados, k),
    ];

    let mejorKCosto = Infinity;
    let mejorKRutas = null;
    let mejorKDist = 0;
    let mejorKMakespan = 0;

    for (const franjas of particiones) {
      const optFranjas = franjas.map((f) => optimizarGrasp2Opt(f, depX, depY));
      let distTotal = 0;
      let makespan = 0;
      let usados = 0;
      for (const r of optFranjas) {
        if (!r.length) continue;
        usados++;
        const dr = costoDistanciaRuta(r, depX, depY);
        const tr = dr * minCuadra + r.length * tServicio;
        distTotal += dr;
        if (tr > makespan) makespan = tr;
      }
      const costoTotal = distTotal * cCuadra + usados * cVeh + makespan * cMin;
      if (costoTotal < mejorKCosto) {
        mejorKCosto = costoTotal;
        mejorKDist = distTotal;
        mejorKMakespan = makespan;
        mejorKRutas = optFranjas.map((r, i) => ({
          vehiculo: vehiculos[i].id,
          paradas: r.map((p) => p.id),
        }));
      }
    }

    console.log(
      `     ${k}     | ${String(mejorKDist + " cuadras").padStart(11)} | ${String(mejorKMakespan + " min").padStart(11)} | ${String("$" + k * cVeh).padStart(11)} | ${String("$" + mejorKCosto).padStart(12)}`
    );

    if (mejorKCosto < menorCosto) {
      menorCosto = mejorKCosto;
      mejorPlan = { rutas: mejorKRutas };
      mejorK = k;
    }
  }

  console.log("-".repeat(68));
  console.log(`-> ÓPTIMO ELEGIDO: ${mejorK} vehículo(s) con COSTO TOTAL = $${menorCosto}`);

  const carpetaRespuestas = path.join(__dirname, "respuestas");
  if (!fs.existsSync(carpetaRespuestas)) {
    fs.mkdirSync(carpetaRespuestas, { recursive: true });
  }

  const nombreDataset = path.basename(path.resolve(carpeta));
  const rutaFinal = archivoSalida
    ? path.isAbsolute(archivoSalida)
      ? archivoSalida
      : path.join(carpetaRespuestas, path.basename(archivoSalida))
    : path.join(carpetaRespuestas, `plan_${nombreDataset}.json`);

  fs.writeFileSync(rutaFinal, JSON.stringify(mejorPlan, null, 2) + "\n", "utf8");
  fs.writeFileSync(path.join(carpetaRespuestas, "plan.json"), JSON.stringify(mejorPlan, null, 2) + "\n", "utf8");
  console.log(`-> Plan guardado en carpeta respuestas: ${rutaFinal}`);
  console.log("=".repeat(68));
}

const defaultDir = fs.existsSync(path.join(__dirname, "Datos", "mundo.json"))
  ? path.join(__dirname, "Datos")
  : path.join(__dirname, "datos", "ejemplo");
const carpetaArg = process.argv[2] || defaultDir;
const salidaArg = process.argv[3] || null;
resolver(carpetaArg, salidaArg);
