/**
 * Script de respaldo en Node.js (ejecutar.js - Rama solucion-2-premium)
 * Ejecuta la arquitectura para el Evento 2 (Pedidos Premium con costo por minuto de demora):
 * - Geometría 0-360° con recorte de huecos y detección de campo 'premium'.
 * - GRASP Ponderado por Prioridad + 2-Opt Sensible a Latencia + Or-Opt (Relocate).
 * - Evaluación de k autos (incluyendo modalidad de vehículo express para Premium).
 */
const fs = require("fs");
const path = require("path");

function distanciaManhattan(x1, y1, x2, y2) {
  return Math.abs(x1 - x2) + Math.abs(y1 - y2);
}

function esPremium(val) {
  if (typeof val === "boolean") return val;
  if (val === null || val === undefined) return false;
  if (typeof val === "number") return val !== 0;
  const s = String(val).trim().toLowerCase();
  return ["1", "true", "si", "sí", "verdadero"].includes(s);
}

function calcularAngulosYDistancias(pedidos, depX, depY, umbralHueco = 12.0) {
  const resultado = pedidos.map((p) => {
    const px = Number(p.x);
    const py = Number(p.y);
    const pid = Number(p.id);
    const peso = Number(p.peso || 0);
    const premium = esPremium(p.premium);
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
      premium,
      angulo: Number(angulo.toFixed(4)),
      angulo_util: 0.0,
      distancia_deposito: distDep,
    };
  });

  resultado.sort(
    (a, b) =>
      a.angulo - b.angulo ||
      (a.premium === b.premium ? 0 : a.premium ? -1 : 1) ||
      a.distancia_deposito - b.distancia_deposito
  );

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

function dividirVehiculoExpressPremium(pedidos, k) {
  if (k < 2) return [pedidos.slice()];
  const premiums = pedidos.filter((p) => p.premium);
  const normales = pedidos.filter((p) => !p.premium);
  if (!premiums.length || !normales.length) return dividirBalanceado(pedidos, k);
  return [premiums, ...dividirBalanceado(normales, k - 1)];
}

function dividirEquilibrandoPremiums(pedidos, k) {
  if (!pedidos.length || k <= 1) return pedidos.length ? [pedidos.slice()] : [];
  const idxPrem = [];
  pedidos.forEach((p, idx) => {
    if (p.premium) idxPrem.push(idx);
  });
  if (idxPrem.length < k) return dividirBalanceado(pedidos, k);
  const franjas = [];
  let ini = 0;
  for (let v = 1; v < k; v++) {
    const cortePrem = Math.floor((v * idxPrem.length) / k);
    const posCorte = Math.floor((idxPrem[cortePrem - 1] + idxPrem[cortePrem]) / 2) + 1;
    if (posCorte > ini) {
      franjas.push(pedidos.slice(ini, posCorte));
      ini = posCorte;
    }
  }
  if (ini < pedidos.length) franjas.push(pedidos.slice(ini));
  return franjas.filter((f) => f.length > 0);
}

function evaluarMetricasRuta(paradas, params) {
  if (!paradas.length) return { dist: 0, tiempo: 0, minPrem: 0, costoCompuesto: 0 };
  let posX = params.depX;
  let posY = params.depY;
  let tiempo = 0;
  let dist = 0;
  let minPrem = 0;

  for (const p of paradas) {
    const d = distanciaManhattan(posX, posY, p.x, p.y);
    tiempo += d * params.minCuadra;
    dist += d;
    posX = p.x;
    posY = p.y;
    if (p.premium) {
      minPrem += tiempo;
    }
    tiempo += params.tServicio;
  }
  const dReg = distanciaManhattan(posX, posY, params.depX, params.depY);
  tiempo += dReg * params.minCuadra;
  dist += dReg;

  const costoCompuesto = dist * params.cCuadra + minPrem * params.cPrem;
  return { dist, tiempo, minPrem, costoCompuesto };
}

function busquedaLocal2OptYRelocate(ruta, params) {
  if (ruta.length <= 1) return ruta.slice();
  let mejor = ruta.slice();
  let mejorCosto = evaluarMetricasRuta(mejor, params).costoCompuesto;

  // 1. Probar ruta invertida
  const inv = mejor.slice().reverse();
  const cInv = evaluarMetricasRuta(inv, params).costoCompuesto;
  if (cInv < mejorCosto) {
    mejor = inv;
    mejorCosto = cInv;
  }

  let mejoro = true;
  while (mejoro) {
    mejoro = false;
    // 2. 2-Opt guiado por costo compuesto
    for (let i = 0; i < mejor.length - 1; i++) {
      for (let j = i + 1; j < mejor.length; j++) {
        const rev = mejor.slice(i, j + 1).reverse();
        const cand = [...mejor.slice(0, i), ...rev, ...mejor.slice(j + 1)];
        const c = evaluarMetricasRuta(cand, params).costoCompuesto;
        if (c < mejorCosto - 1e-6) {
          mejor = cand;
          mejorCosto = c;
          mejoro = true;
        }
      }
    }
    // 3. Or-Opt / Relocate (reubicar un nodo para adelantar entregas premium)
    for (let i = 0; i < mejor.length; i++) {
      const nodo = mejor[i];
      const resto = [...mejor.slice(0, i), ...mejor.slice(i + 1)];
      for (let j = 0; j < mejor.length; j++) {
        if (i === j) continue;
        const cand = [...resto.slice(0, j), nodo, ...resto.slice(j)];
        const c = evaluarMetricasRuta(cand, params).costoCompuesto;
        if (c < mejorCosto - 1e-6) {
          mejor = cand;
          mejorCosto = c;
          mejoro = true;
          break;
        }
      }
      if (mejoro) break;
    }
  }
  return mejor;
}

function optimizarGrasp2Opt(franja, params) {
  if (franja.length <= 1) return franja.slice();
  let mejorRuta = null;
  let menorCosto = Infinity;
  const alphas = [0.0, 0.15, 0.25, 0.35];
  const pesosPrem = [0.0, 0.35, 0.6, 1.0];

  let seed = 42;
  function rand() {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  }

  for (let it = 0; it < 32; it++) {
    const alpha = it < 4 ? 0.0 : alphas[it % alphas.length];
    const pesoPrem = pesosPrem[it % pesosPrem.length];
    const pendientes = franja.slice();
    const ruta = [];
    let ax = params.depX,
      ay = params.depY;

    while (pendientes.length > 0) {
      const hayPrem = pendientes.some((p) => p.premium);
      const base = pesoPrem === 0.0 && hayPrem ? pendientes.filter((p) => p.premium) : pendientes;
      const dists = base.map((p) => {
        const dReal = distanciaManhattan(ax, ay, p.x, p.y);
        const factor = p.premium ? pesoPrem : 1.0;
        return { d: dReal * factor, p };
      });
      const dMin = Math.min(...dists.map((x) => x.d));
      const dMax = Math.max(...dists.map((x) => x.d));
      const umbral = dMin + alpha * (dMax - dMin);
      const rcl = dists.filter((x) => x.d <= umbral + 1e-9).map((x) => x.p);
      const elegido = rcl[Math.floor(rand() * rcl.length)];
      ruta.push(elegido);
      pendientes.splice(pendientes.indexOf(elegido), 1);
      ax = elegido.x;
      ay = elegido.y;
    }

    const opt = busquedaLocal2OptYRelocate(ruta, params);
    const c = evaluarMetricasRuta(opt, params).costoCompuesto;
    if (c < menorCosto) {
      menorCosto = c;
      mejorRuta = opt;
    }
  }
  return mejorRuta;
}

function resolver(carpeta, archivoSalida) {
  const mundo = JSON.parse(fs.readFileSync(path.join(carpeta, "mundo.json"), "utf8"));
  const pedidos = JSON.parse(fs.readFileSync(path.join(carpeta, "pedidos.json"), "utf8"));
  const vehiculos = JSON.parse(fs.readFileSync(path.join(carpeta, "vehiculos.json"), "utf8"));

  const params = {
    depX: mundo.deposito_x ?? 0,
    depY: mundo.deposito_y ?? 0,
    minCuadra: mundo.min_por_cuadra ?? 3,
    tServicio: mundo.tiempo_servicio ?? 5,
    cCuadra: mundo.costo_por_cuadra ?? 3,
    cVeh: mundo.costo_por_vehiculo ?? 60,
    cMin: mundo.costo_por_minuto_total ?? 1,
    cPrem: mundo.costo_por_minuto_premium ?? 1,
  };

  const pedidosOrdenados = calcularAngulosYDistancias(pedidos, params.depX, params.depY);
  const cantPrem = pedidosOrdenados.filter((p) => p.premium).length;

  console.log("=".repeat(78));
  console.log(`DATASET: ${carpeta}`);
  console.log(
    `Depósito: (${params.depX}, ${params.depY}) | Pedidos: ${pedidos.length} (Premium: ${cantPrem}) | Vehículos: ${vehiculos.length}`
  );
  console.log(
    `[Fase 1 - Geometría] Ángulo real: ${pedidosOrdenados[0].angulo}° a ${pedidosOrdenados[pedidosOrdenados.length - 1].angulo}° | Ángulo útil (sin huecos): ${pedidosOrdenados[pedidosOrdenados.length - 1].angulo_util}°`
  );
  console.log("-".repeat(78));
  console.log(" Autos(k) |  Distancia  |  Makespan  |  Min.Prem  | Costo Autos | COSTO TOTAL ");
  console.log("-".repeat(78));

  let mejorPlan = null;
  let menorCosto = Infinity;
  let mejorK = 1;

  for (let k = 1; k <= vehiculos.length; k++) {
    const particiones = [
      dividirPorAnguloUtil(pedidosOrdenados, k),
      dividirBalanceado(pedidosOrdenados, k),
    ];
    if (cantPrem > 0 && k >= 2) {
      particiones.push(dividirVehiculoExpressPremium(pedidosOrdenados, k));
      particiones.push(dividirEquilibrandoPremiums(pedidosOrdenados, k));
    }

    let mejorKCosto = Infinity;
    let mejorKRutas = null;
    let mejorKDist = 0;
    let mejorKMakespan = 0;
    let mejorKMinPrem = 0;

    for (const franjas of particiones) {
      const optFranjas = franjas.map((f) => optimizarGrasp2Opt(f, params));
      let distTotal = 0;
      let makespan = 0;
      let minPremTotal = 0;
      let usados = 0;
      for (const r of optFranjas) {
        if (!r.length) continue;
        usados++;
        const m = evaluarMetricasRuta(r, params);
        distTotal += m.dist;
        minPremTotal += m.minPrem;
        if (m.tiempo > makespan) makespan = m.tiempo;
      }
      const costoTotal =
        distTotal * params.cCuadra +
        usados * params.cVeh +
        makespan * params.cMin +
        minPremTotal * params.cPrem;

      if (costoTotal < mejorKCosto) {
        mejorKCosto = costoTotal;
        mejorKDist = distTotal;
        mejorKMakespan = makespan;
        mejorKMinPrem = minPremTotal;
        mejorKRutas = optFranjas.map((r, i) => ({
          vehiculo: vehiculos[i].id,
          paradas: r.map((p) => p.id),
        }));
      }
    }

    console.log(
      `    ${k}     | ${String(mejorKDist + " cuad").padStart(11)} | ${String(mejorKMakespan + " min").padStart(10)} | ${String(mejorKMinPrem + " min").padStart(10)} | ${String("$" + k * params.cVeh).padStart(11)} | ${String("$" + mejorKCosto).padStart(12)}`
    );

    if (mejorKCosto < menorCosto) {
      menorCosto = mejorKCosto;
      mejorPlan = { rutas: mejorKRutas };
      mejorK = k;
    }
  }

  console.log("-".repeat(78));
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
  console.log("=".repeat(78));
}

const defaultDir = fs.existsSync(path.join(__dirname, "Datos", "mundo.json"))
  ? path.join(__dirname, "Datos")
  : path.join(__dirname, "datos", "ejemplo");
const carpetaArg = process.argv[2] || defaultDir;
const salidaArg = process.argv[3] || null;
resolver(carpetaArg, salidaArg);
